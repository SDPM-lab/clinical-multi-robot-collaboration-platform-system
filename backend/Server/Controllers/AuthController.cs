using System.Security.Claims;
using System.Net;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Server.Models;
using Server.Requests;
using Server.Services.Auth;

namespace Server.Controllers;

[ApiController]
[Route("api/auth")]
[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public sealed class AuthController(AccountStore accounts, IAntiforgery antiforgery, IWebHostEnvironment environment) : ControllerBase
{
    // SPA 先取得防偽權杖，後續寫入請求用 X-CSRF-TOKEN 標頭傳送。
    [AllowAnonymous, HttpGet("csrf")]
    public IActionResult Csrf() => Ok(new { token = antiforgery.GetAndStoreTokens(HttpContext).RequestToken });

    [AllowAnonymous, HttpPost("register"), EnableRateLimiting("auth")]
    public async Task<IActionResult> Register(RegisterRequest request)
    {
        if (request.Name.Trim().Length < 2) return BadRequest(new { code = "invalid_name" });
        var account = await accounts.RegisterAsync(request.Email, request.Name, request.Password);
        if (account is null) return Conflict(new { code = "email_exists" });
        await SignInAsync(account, rememberMe: false);
        return StatusCode(201, AccountStore.Profile(account));
    }

    [AllowAnonymous, HttpPost("login"), EnableRateLimiting("auth")]
    public async Task<IActionResult> Login(LoginRequest request)
    {
        var account = await accounts.ValidateAsync(request.Email, request.Password);
        if (account is null) return Unauthorized(new { code = "invalid_credentials" });
        await SignInAsync(account, request.RememberMe);
        return Ok(AccountStore.Profile(account));
    }

    [AllowAnonymous, HttpPost("dev-login"), EnableRateLimiting("auth")]
    public async Task<IActionResult> DevelopmentLogin()
    {
        var remoteAddress = HttpContext.Connection.RemoteIpAddress;
        if (!environment.IsDevelopment() || remoteAddress is null || !IPAddress.IsLoopback(remoteAddress))
            return NotFound();

        var account = await accounts.GetOrCreateDevelopmentAccountAsync();
        await SignInAsync(account, rememberMe: false);
        return Ok(AccountStore.Profile(account));
    }

    [HttpGet("me")]
    public async Task<IActionResult> Me()
    {
        var account = await accounts.FindByIdAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        return account is null ? Unauthorized(new { code = "session_expired" }) : Ok(AccountStore.Profile(account));
    }

    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        return NoContent();
    }

    [HttpPatch("profile"), RequestSizeLimit(5_000_000)]
    public async Task<IActionResult> Profile(UpdateProfileRequest request)
    {
        if (request.Name.Trim().Length < 2) return BadRequest(new { code = "invalid_name" });
        if (!ValidAvatar(request.AvatarUrl)) return BadRequest(new { code = "invalid_avatar" });
        var account = await accounts.UpdateProfileAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!, request.Name, request.AvatarUrl);
        return account is null ? Unauthorized(new { code = "session_expired" }) : Ok(AccountStore.Profile(account));
    }

    private Task SignInAsync(UserAccount account, bool rememberMe)
    {
        var identity = new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier, account.Id)], CookieAuthenticationDefaults.AuthenticationScheme);
        return HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, new ClaimsPrincipal(identity),
            new AuthenticationProperties { IsPersistent = rememberMe,
                ExpiresUtc = DateTimeOffset.UtcNow.Add(rememberMe ? TimeSpan.FromDays(14) : TimeSpan.FromHours(8)) });
    }

    private static bool ValidAvatar(string? avatar)
    {
        if (avatar is null) return true;
        var comma = avatar.IndexOf(',');
        if (comma < 0) return false;
        var mime = avatar[..comma];
        if (mime is not ("data:image/png;base64" or "data:image/jpeg;base64" or "data:image/webp;base64")) return false;
        try
        {
            var bytes = Convert.FromBase64String(avatar[(comma + 1)..]);
            if (bytes.Length > 3 * 1024 * 1024 || bytes.Length < 12) return false;
            return mime switch
            {
                "data:image/png;base64" => bytes.AsSpan(0, 8).SequenceEqual(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 }),
                "data:image/jpeg;base64" => bytes[0] == 255 && bytes[1] == 216 && bytes[2] == 255,
                _ => bytes.AsSpan(0, 4).SequenceEqual("RIFF"u8) && bytes.AsSpan(8, 4).SequenceEqual("WEBP"u8)
            };
        }
        catch (FormatException) { return false; }
    }
}
