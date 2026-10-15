var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var api = app.MapGroup("/api").RequireAuthorization();

api.MapGet("/loans/{id}", GetLoan).WithName("GetLoan");
api.MapPost("/loans", CreateLoan).RequireAuthorization("LoansWrite");
app.MapGet("/health", () => "ok").AllowAnonymous().WithName("Health");

app.Run();

static IResult GetLoan(string id) => Results.Ok(id);
static IResult CreateLoan() => Results.Ok();
