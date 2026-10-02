using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace EakgDotnetExtract;

internal static class Program
{
    private const string DetectorId = "dotnet_roslyn";
    private const string DetectorVersion = "2.0.0";

    public static int Main(string[] args)
    {
        try
        {
            var repo = GetArg(args, "--repo") ?? throw new ArgumentException("--repo required");
            var repoId = GetArg(args, "--repo-id") ?? "unknown";
            var commit = GetArg(args, "--commit") ?? "unknown";
            var apiProject = GetArg(args, "--api-project-path") ?? "";

            var root = Path.GetFullPath(repo);
            if (!Directory.Exists(root))
            {
                Console.Error.WriteLine($"repo not found: {root}");
                return 2;
            }

            var searchRoots = new List<string>();
            if (!string.IsNullOrWhiteSpace(apiProject))
            {
                var api = Path.Combine(root, apiProject.Replace('/', Path.DirectorySeparatorChar));
                if (Directory.Exists(api))
                    searchRoots.Add(api);
            }
            if (searchRoots.Count == 0)
                searchRoots.Add(root);

            var excluded = LoadCompileRemoves(root);
            var operations = new List<OpDto>();

            foreach (var search in searchRoots)
            {
                foreach (var file in Directory.EnumerateFiles(search, "*Controller.cs", SearchOption.AllDirectories))
                {
                    var rel = Path.GetRelativePath(root, file).Replace('\\', '/');
                    if (excluded.Any(ex =>
                            rel.EndsWith(ex, StringComparison.OrdinalIgnoreCase)
                            || rel.Contains(ex, StringComparison.OrdinalIgnoreCase)))
                        continue;
                    if (Path.GetFileName(file).Contains("Startup_Old", StringComparison.OrdinalIgnoreCase))
                        continue;

                    var text = File.ReadAllText(file);
                    var tree = CSharpSyntaxTree.ParseText(text, path: file);
                    var rootNode = tree.GetCompilationUnitRoot();
                    foreach (var cls in rootNode.DescendantNodes().OfType<ClassDeclarationSyntax>())
                    {
                        var name = cls.Identifier.Text;
                        if (!name.EndsWith("Controller", StringComparison.Ordinal))
                            continue;

                        var classAttrs = cls.AttributeLists.SelectMany(a => a.Attributes).ToList();
                        var classRoute = LastRoute(classAttrs);
                        string? classAuth = null;
                        var classAuthSource = "unknown";
                        if (HasAllowAnonymous(classAttrs))
                        {
                            classAuth = "AllowAnonymous";
                            classAuthSource = "attribute";
                        }
                        else if (TryAuthorize(classAttrs, out var pol))
                        {
                            classAuth = pol;
                            classAuthSource = "class-level";
                        }

                        foreach (var method in cls.Members.OfType<MethodDeclarationSyntax>())
                        {
                            var attrs = method.AttributeLists.SelectMany(a => a.Attributes).ToList();
                            if (!TryHttp(attrs, out var httpMethod, out var httpTmpl))
                                continue;

                            var action = method.Identifier.Text;
                            var actionRoute = LastRoute(attrs);
                            var path = JoinRoutes(classRoute, actionRoute, httpTmpl);
                            if (path.Contains("[controller]", StringComparison.OrdinalIgnoreCase))
                            {
                                var token = name.EndsWith("Controller", StringComparison.Ordinal)
                                    ? name[..^"Controller".Length]
                                    : name;
                                path = Regex.Replace(path, "\\[controller\\]", token, RegexOptions.IgnoreCase);
                            }

                            var authz = classAuth;
                            var authzSource = classAuthSource;
                            if (HasAllowAnonymous(attrs))
                            {
                                authz = "AllowAnonymous";
                                authzSource = "attribute";
                            }
                            else if (TryAuthorize(attrs, out var mPol))
                            {
                                authz = mPol;
                                authzSource = "attribute";
                            }

                            var line = method.GetLocation().GetLineSpan().StartLinePosition.Line + 1;
                            var key = $"{httpMethod}:{path}:{name}.{action}";
                            operations.Add(new OpDto
                            {
                                OperationKey = key,
                                HttpMethod = httpMethod,
                                HttpPath = path,
                                Controller = name,
                                Action = action,
                                AuthzPolicy = authz,
                                AuthzSource = authzSource,
                                ReadOnly = httpMethod is "GET" or "HEAD" or "OPTIONS",
                                Evidence =
                                [
                                    new EvDto
                                    {
                                        RepositoryId = repoId,
                                        CommitSha = commit,
                                        FilePath = rel,
                                        LineStart = line,
                                        LineEnd = line,
                                        DetectorId = DetectorId,
                                        DetectorVersion = DetectorVersion,
                                        Confidence = 0.97
                                    }
                                ]
                            });
                        }
                    }
                }
            }

            var payload = new { detector = DetectorId, detectorVersion = DetectorVersion, operations };
            Console.WriteLine(JsonSerializer.Serialize(payload, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
                WriteIndented = false
            }));
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }

    private static string? GetArg(string[] args, string name)
    {
        for (var i = 0; i < args.Length - 1; i++)
            if (args[i] == name)
                return args[i + 1];
        return null;
    }

    private static HashSet<string> LoadCompileRemoves(string root)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var csproj in Directory.EnumerateFiles(root, "*.csproj", SearchOption.AllDirectories))
        {
            var text = File.ReadAllText(csproj);
            foreach (Match m in Regex.Matches(text, "<Compile\\s+Remove=\"([^\"]+)\"", RegexOptions.IgnoreCase))
                set.Add(m.Groups[1].Value.Replace('\\', '/'));
        }
        return set;
    }

    private static string? LastRoute(IEnumerable<AttributeSyntax> attrs)
    {
        string? last = null;
        foreach (var a in attrs)
        {
            var n = AttrName(a);
            if (n is not ("Route" or "RouteAttribute"))
                continue;
            if (a.ArgumentList?.Arguments.Count > 0
                && a.ArgumentList.Arguments[0].Expression is LiteralExpressionSyntax lit
                && lit.IsKind(SyntaxKind.StringLiteralExpression))
                last = lit.Token.ValueText;
        }
        return last;
    }

    private static string AttrName(AttributeSyntax a)
    {
        return a.Name switch
        {
            IdentifierNameSyntax id => id.Identifier.Text,
            QualifiedNameSyntax q => q.Right.Identifier.Text,
            AliasQualifiedNameSyntax aq => aq.Name.Identifier.Text,
            _ => a.Name.ToString()
        };
    }

    private static bool TryHttp(IEnumerable<AttributeSyntax> attrs, out string method, out string? template)
    {
        method = "";
        template = null;
        foreach (var a in attrs)
        {
            var n = AttrName(a);
            string? m = n switch
            {
                "HttpGet" or "HttpGetAttribute" => "GET",
                "HttpPost" or "HttpPostAttribute" => "POST",
                "HttpPut" or "HttpPutAttribute" => "PUT",
                "HttpDelete" or "HttpDeleteAttribute" => "DELETE",
                "HttpPatch" or "HttpPatchAttribute" => "PATCH",
                _ => null
            };
            if (m is null)
                continue;
            method = m;
            if (a.ArgumentList?.Arguments.Count > 0
                && a.ArgumentList.Arguments[0].Expression is LiteralExpressionSyntax lit
                && lit.IsKind(SyntaxKind.StringLiteralExpression))
                template = lit.Token.ValueText;
            return true;
        }
        return false;
    }

    private static bool HasAllowAnonymous(IEnumerable<AttributeSyntax> attrs) =>
        attrs.Any(a =>
        {
            var n = AttrName(a);
            return n is "AllowAnonymous" or "AllowAnonymousAttribute";
        });

    private static bool TryAuthorize(IEnumerable<AttributeSyntax> attrs, out string policy)
    {
        policy = "Authorize";
        foreach (var a in attrs)
        {
            var n = AttrName(a);
            if (n is not ("Authorize" or "AuthorizeAttribute"))
                continue;
            if (a.ArgumentList is null)
                return true;
            foreach (var arg in a.ArgumentList.Arguments)
            {
                if (arg.NameEquals?.Name.Identifier.Text == "Policy")
                {
                    if (arg.Expression is LiteralExpressionSyntax lit)
                        policy = lit.Token.ValueText;
                    else
                        policy = arg.Expression.ToString().Trim('"');
                }
            }
            return true;
        }
        return false;
    }

    /// <summary>Match Python _join_routes: class, action Route, then Http* template.</summary>
    private static string JoinRoutes(string? classRoute, string? actionRoute, string? httpTemplate)
    {
        var parts = new List<string>();
        foreach (var p in new[] { classRoute, actionRoute, httpTemplate })
        {
            if (string.IsNullOrWhiteSpace(p))
                continue;
            if (p.StartsWith('/'))
                return p;
            parts.Add(p.Trim().Trim('/'));
        }
        return parts.Count == 0 ? "/" : "/" + string.Join("/", parts);
    }

    private sealed class OpDto
    {
        public string OperationKey { get; set; } = "";
        public string HttpMethod { get; set; } = "";
        public string HttpPath { get; set; } = "";
        public string Controller { get; set; } = "";
        public string Action { get; set; } = "";
        public string? AuthzPolicy { get; set; }
        public string AuthzSource { get; set; } = "unknown";
        public bool ReadOnly { get; set; }
        public EvDto[] Evidence { get; set; } = [];
    }

    private sealed class EvDto
    {
        public string RepositoryId { get; set; } = "";
        public string CommitSha { get; set; } = "";
        public string FilePath { get; set; } = "";
        public int LineStart { get; set; }
        public int LineEnd { get; set; }
        public string DetectorId { get; set; } = "";
        public string DetectorVersion { get; set; } = "";
        public double Confidence { get; set; }
    }
}
