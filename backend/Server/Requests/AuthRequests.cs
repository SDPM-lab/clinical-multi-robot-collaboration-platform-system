using System.ComponentModel.DataAnnotations;

namespace Server.Requests;

public sealed class RegisterRequest
{
    [Required, StringLength(40, MinimumLength = 2)]
    public string Name { get; set; } = "";
    [Required, EmailAddress, StringLength(254)]
    public string Email { get; set; } = "";
    [Required, StringLength(128, MinimumLength = 6)]
    public string Password { get; set; } = "";
}

public sealed class LoginRequest
{
    [Required, EmailAddress, StringLength(254)]
    public string Email { get; set; } = "";
    [Required, StringLength(128)]
    public string Password { get; set; } = "";
    public bool RememberMe { get; set; }
}

public sealed class UpdateProfileRequest
{
    [Required, StringLength(40, MinimumLength = 2)]
    public string Name { get; set; } = "";
    [StringLength(4_200_000)]
    public string? AvatarUrl { get; set; }
}
