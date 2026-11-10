namespace Server.Models;

// 僅供後端保存；PasswordHash 不可直接回傳前端。
public sealed record UserAccount(string Id, string Email, string Name, string PasswordHash,
    DateTimeOffset CreatedAt, string? AvatarUrl = null);

public sealed record UserProfile(string Id, string Email, string Name, string? AvatarUrl);
