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
    private const string DetectorVersion = "2.1.0";

    private static readonly HashSet<string> SkipDirNames = new(StringComparer.OrdinalIgnoreCase)
    {
        ".git", "bin", "obj", "node_modules", "packages", "TestResults", ".vs"
    };

    private static readonly Dictionary<string, string> MapMethods = new(StringComparer.Ordinal)
    {
        ["MapGet"] = "GET",
        ["MapPost"] = "POST",
        ["MapPut"] = "PUT",
        ["MapDelete"] = "DELETE",
        ["MapPatch"] = "PATCH",
    };

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
            var seenKeys = new HashSet<string>(StringComparer.Ordinal);

            foreach (var search in searchRoots)
            {
                foreach (var file in EnumerateCsFiles(search))
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

                    ExtractControllers(rootNode, rel, repoId, commit, operations, seenKeys);
                    ExtractMinimalApis(rootNode, rel, repoId, commit, operations, seenKeys);
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

    private static IEnumerable<string> EnumerateCsFiles(string search)
    {
        var stack = new Stack<string>();
        stack.Push(search);
        while (stack.Count > 0)
        {
            var dir = stack.Pop();
            string[]? children = null;
            try { children = Directory.GetDirectories(dir); }
            catch { /* skip */ }
            if (children != null)
            {
                foreach (var child in children)
                {
                    var name = Path.GetFileName(child);
                    if (SkipDirNames.Contains(name))
                        continue;
                    stack.Push(child);
                }
            }
            string[]? files = null;
            try { files = Directory.GetFiles(dir, "*.cs"); }
            catch { /* skip */ }
            if (files == null)
                continue;
            foreach (var f in files)
                yield return f;
        }
    }

    private static void ExtractControllers(
        CompilationUnitSyntax rootNode,
        string rel,
        string repoId,
        string commit,
        List<OpDto> operations,
        HashSet<string> seenKeys)
    {
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
                if (!seenKeys.Add(key))
                    continue;
                operations.Add(MakeOp(key, httpMethod, path, name, action, authz, authzSource, repoId, commit, rel, line));
            }
        }
    }

    private static void ExtractMinimalApis(
        CompilationUnitSyntax rootNode,
        string rel,
        string repoId,
        string commit,
        List<OpDto> operations,
        HashSet<string> seenKeys)
    {
        // Scope: method bodies + top-level statements (Program.cs)
        var scopes = new List<(SyntaxNode Body, string FileStem)>();
        var fileStem = Path.GetFileNameWithoutExtension(rel);

        foreach (var method in rootNode.DescendantNodes().OfType<MethodDeclarationSyntax>())
        {
            if (method.Body != null)
                scopes.Add((method.Body, fileStem));
        }
        foreach (var local in rootNode.DescendantNodes().OfType<LocalFunctionStatementSyntax>())
        {
            if (local.Body != null)
                scopes.Add((local.Body, fileStem));
        }
        // Top-level statements live as GlobalStatementSyntax under the compilation unit
        var globals = rootNode.Members.OfType<GlobalStatementSyntax>().ToList();
        if (globals.Count > 0)
            scopes.Add((rootNode, fileStem));

        foreach (var (scope, stem) in scopes)
            ExtractMinimalInScope(scope, stem, rel, repoId, commit, operations, seenKeys);
    }

    private static void ExtractMinimalInScope(
        SyntaxNode scope,
        string fileStem,
        string rel,
        string repoId,
        string commit,
        List<OpDto> operations,
        HashSet<string> seenKeys)
    {
        // groupVar -> prefix path
        var groups = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var node in scope.DescendantNodes())
        {
            // var g = app.MapGroup("/api");  or  var g = app.MapGroup("/api").RequireAuthorization();
            if (node is VariableDeclaratorSyntax vdecl
                && vdecl.Initializer?.Value is InvocationExpressionSyntax groupChain)
            {
                var mapGroup = FindInvocationInChain(groupChain, "MapGroup");
                if (mapGroup != null)
                {
                    var prefix = FirstStringArg(mapGroup) ?? "";
                    var receiverPrefix = ResolveReceiverPrefix(mapGroup.Expression, groups);
                    groups[vdecl.Identifier.Text] = JoinGroupPath(receiverPrefix, prefix);
                }
                continue;
            }

            if (node is not InvocationExpressionSyntax inv)
                continue;

            var name = GetInvocationName(inv);
            if (name is null)
                continue;

            if (name == "MapMethods")
            {
                // MapMethods(pattern, httpMethods, handler)
                var path = FirstStringArg(inv);
                if (path is null)
                    continue;
                var methods = MapMethodsHttpList(inv);
                if (methods.Count == 0)
                    continue;
                var prefix = ResolveReceiverPrefix(inv.Expression, groups);
                var fullPath = JoinGroupPath(prefix, path);
                var action = ResolveMinimalAction(inv, fullPath, "ANY");
                var (authz, authzSource) = ResolveFluentAuthz(inv, groups);
                var line = inv.GetLocation().GetLineSpan().StartLinePosition.Line + 1;
                var controller = $"MinimalApi:{fileStem}";
                foreach (var httpMethod in methods)
                {
                    var key = $"{httpMethod}:{fullPath}:{controller}.{action}";
                    if (!seenKeys.Add(key))
                        continue;
                    operations.Add(MakeOp(key, httpMethod, fullPath, controller, action, authz, authzSource, repoId, commit, rel, line));
                }
                continue;
            }

            if (!MapMethods.TryGetValue(name, out var httpMethodSingle))
                continue;

            var route = FirstStringArg(inv);
            if (route is null)
                continue;
            var groupPrefix = ResolveReceiverPrefix(inv.Expression, groups);
            var httpPath = JoinGroupPath(groupPrefix, route);
            var act = ResolveMinimalAction(inv, httpPath, httpMethodSingle);
            var (az, azSrc) = ResolveFluentAuthz(inv, groups);
            // Group-level RequireAuthorization on the MapGroup variable
            if (azSrc == "unknown" && inv.Expression is MemberAccessExpressionSyntax ma
                && ma.Expression is IdentifierNameSyntax id
                && groups.ContainsKey(id.Identifier.Text))
            {
                // leave unknown unless chain has auth — already handled
            }
            var ln = inv.GetLocation().GetLineSpan().StartLinePosition.Line + 1;
            var ctrl = $"MinimalApi:{fileStem}";
            var opKey = $"{httpMethodSingle}:{httpPath}:{ctrl}.{act}";
            if (!seenKeys.Add(opKey))
                continue;
            operations.Add(MakeOp(opKey, httpMethodSingle, httpPath, ctrl, act, az, azSrc, repoId, commit, rel, ln));
        }
    }

    private static string? ResolveReceiverPrefix(
        ExpressionSyntax expression,
        Dictionary<string, string> groups)
    {
        // app.MapGet → no prefix; g.MapGet → groups[g]; app.MapGroup(...).MapGet not typical
        if (expression is MemberAccessExpressionSyntax ma)
        {
            if (ma.Expression is IdentifierNameSyntax id
                && groups.TryGetValue(id.Identifier.Text, out var p))
                return p;
            // Nested: group.MapGroup("/x") already stored with joined prefix
        }
        return null;
    }

    private static (string? authz, string authzSource) ResolveFluentAuthz(
        InvocationExpressionSyntax mapInv,
        Dictionary<string, string> groups)
    {
        // Walk outward: MapGet(...).RequireAuthorization("P").WithName("x")
        // Parents alternate MemberAccessExpression / InvocationExpression.
        SyntaxNode? cur = mapInv.Parent;
        string? authz = null;
        var source = "unknown";

        while (cur != null)
        {
            if (cur is InvocationExpressionSyntax outer && outer != mapInv)
            {
                var n = GetInvocationName(outer);
                if (n is "AllowAnonymous")
                {
                    authz = "AllowAnonymous";
                    source = "attribute";
                }
                else if (n is "RequireAuthorization")
                {
                    authz = FirstStringArg(outer) ?? "Authorize";
                    source = "attribute";
                }
            }
            cur = cur.Parent;
        }

        // Group-level: var g = app.MapGroup("/x").RequireAuthorization();
        if (source == "unknown"
            && mapInv.Expression is MemberAccessExpressionSyntax ma
            && ma.Expression is IdentifierNameSyntax gid
            && groups.ContainsKey(gid.Identifier.Text))
        {
            // Look for RequireAuthorization on the MapGroup initializer chain for this var
            var decl = mapInv.Ancestors().OfType<MethodDeclarationSyntax>().FirstOrDefault()
                       ?? (SyntaxNode?)mapInv.SyntaxTree.GetRoot();
            if (decl != null)
            {
                foreach (var v in decl.DescendantNodes().OfType<VariableDeclaratorSyntax>())
                {
                    if (v.Identifier.Text != gid.Identifier.Text)
                        continue;
                    if (v.Initializer?.Value is not InvocationExpressionSyntax chain)
                        continue;
                    var walk = chain;
                    while (true)
                    {
                        var wn = GetInvocationName(walk);
                        if (wn is "AllowAnonymous")
                        {
                            authz = "AllowAnonymous";
                            source = "class-level";
                            break;
                        }
                        if (wn is "RequireAuthorization")
                        {
                            authz = FirstStringArg(walk) ?? "Authorize";
                            source = "class-level";
                            break;
                        }
                        if (walk.Expression is MemberAccessExpressionSyntax wma
                            && wma.Expression is InvocationExpressionSyntax inner)
                        {
                            walk = inner;
                            continue;
                        }
                        break;
                    }
                }
            }
        }

        return (authz, source);
    }

    private static string ResolveMinimalAction(InvocationExpressionSyntax inv, string path, string method)
    {
        // Prefer .WithName("x") on the fluent chain
        SyntaxNode? cur = inv.Parent;
        while (cur != null)
        {
            if (cur is InvocationExpressionSyntax outer && outer != inv
                && GetInvocationName(outer) == "WithName")
            {
                var named = FirstStringArg(outer);
                if (!string.IsNullOrWhiteSpace(named))
                    return named!;
            }
            cur = cur.Parent;
        }

        // Handler: second arg identifier / member access / lambda
        if (inv.ArgumentList.Arguments.Count >= 2)
        {
            var handler = inv.ArgumentList.Arguments[1].Expression;
            switch (handler)
            {
                case IdentifierNameSyntax id:
                    return id.Identifier.Text;
                case MemberAccessExpressionSyntax ma:
                    return ma.Name.Identifier.Text;
                case SimpleLambdaExpressionSyntax:
                case ParenthesizedLambdaExpressionSyntax:
                    break;
            }
        }

        var slug = Regex.Replace(path.Trim('/'), @"[^A-Za-z0-9]+", "_").Trim('_');
        if (string.IsNullOrEmpty(slug))
            slug = "root";
        return $"{method}_{slug}";
    }

    private static string? GetInvocationName(InvocationExpressionSyntax inv)
    {
        return inv.Expression switch
        {
            IdentifierNameSyntax id => id.Identifier.Text,
            MemberAccessExpressionSyntax ma => ma.Name.Identifier.Text,
            _ => null
        };
    }

    private static InvocationExpressionSyntax? FindInvocationInChain(
        InvocationExpressionSyntax inv,
        string name)
    {
        var walk = inv;
        while (true)
        {
            if (GetInvocationName(walk) == name)
                return walk;
            if (walk.Expression is MemberAccessExpressionSyntax ma
                && ma.Expression is InvocationExpressionSyntax inner)
            {
                walk = inner;
                continue;
            }
            return null;
        }
    }

    private static string? FirstStringArg(InvocationExpressionSyntax inv)
    {
        if (inv.ArgumentList.Arguments.Count == 0)
            return null;
        var expr = inv.ArgumentList.Arguments[0].Expression;
        if (expr is LiteralExpressionSyntax lit && lit.IsKind(SyntaxKind.StringLiteralExpression))
            return lit.Token.ValueText;
        return null;
    }

    private static List<string> MapMethodsHttpList(InvocationExpressionSyntax inv)
    {
        var methods = new List<string>();
        // MapMethods(pattern, httpMethods, handler) — methods are the second argument
        if (inv.ArgumentList.Arguments.Count < 2)
            return methods;
        var expr = inv.ArgumentList.Arguments[1].Expression;
        if (expr is LiteralExpressionSyntax lit && lit.IsKind(SyntaxKind.StringLiteralExpression))
        {
            methods.Add(lit.Token.ValueText.ToUpperInvariant());
            return methods;
        }
        if (expr is ImplicitArrayCreationExpressionSyntax arr)
        {
            foreach (var e in arr.Initializer.Expressions)
            {
                if (e is LiteralExpressionSyntax el && el.IsKind(SyntaxKind.StringLiteralExpression))
                    methods.Add(el.Token.ValueText.ToUpperInvariant());
            }
        }
        else if (expr is ArrayCreationExpressionSyntax ac && ac.Initializer != null)
        {
            foreach (var e in ac.Initializer.Expressions)
            {
                if (e is LiteralExpressionSyntax el && el.IsKind(SyntaxKind.StringLiteralExpression))
                    methods.Add(el.Token.ValueText.ToUpperInvariant());
            }
        }
        else if (expr is CollectionExpressionSyntax col)
        {
            foreach (var el in col.Elements.OfType<ExpressionElementSyntax>())
            {
                if (el.Expression is LiteralExpressionSyntax lit2
                    && lit2.IsKind(SyntaxKind.StringLiteralExpression))
                    methods.Add(lit2.Token.ValueText.ToUpperInvariant());
            }
        }
        return methods;
    }

    private static OpDto MakeOp(
        string key,
        string httpMethod,
        string path,
        string controller,
        string action,
        string? authz,
        string authzSource,
        string repoId,
        string commit,
        string rel,
        int line)
    {
        return new OpDto
        {
            OperationKey = key,
            HttpMethod = httpMethod,
            HttpPath = path,
            Controller = controller,
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
                    Confidence = controller.StartsWith("MinimalApi", StringComparison.Ordinal) ? 0.9 : 0.97
                }
            ]
        };
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

    /// <summary>Join MapGroup prefix with a Map* route (leading slashes treated as relative).</summary>
    private static string JoinGroupPath(string? prefix, string route)
    {
        var parts = new List<string>();
        foreach (var p in new[] { prefix, route })
        {
            if (string.IsNullOrWhiteSpace(p))
                continue;
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
