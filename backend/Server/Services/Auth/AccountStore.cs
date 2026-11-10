using System.Text.Json;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Identity;
using Server.Models;

namespace Server.Services.Auth;

// 單機帳號儲存：密碼只保存雜湊，寫入成功後才更新記憶體。
public sealed class AccountStore(IConfiguration configuration, IWebHostEnvironment environment)
{
    private readonly string _path = Path.Combine(configuration["Auth:DataDirectory"]
        ?? Path.Combine(environment.ContentRootPath, "App_Data"), "accounts.json");
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly PasswordHasher<UserAccount> _hasher = new();
    private List<UserAccount>? _accounts;

    public async Task<UserAccount?> FindByIdAsync(string id)
    {
        await _gate.WaitAsync();
        try { return (await ReadAsync()).Find(account => account.Id == id); }
        finally { _gate.Release(); }
    }

    public async Task<UserAccount?> RegisterAsync(string email, string name, string password)
    {
        await _gate.WaitAsync();
        try
        {
            var accounts = await ReadAsync();
            email = NormalizeEmail(email);
            if (accounts.Any(account => account.Email == email)) return null;
            var account = new UserAccount(Guid.NewGuid().ToString(), email, name.Trim(), "", DateTimeOffset.UtcNow);
            account = account with { PasswordHash = _hasher.HashPassword(account, password) };
            await SaveAsync([.. accounts, account]);
            return account;
        }
        finally { _gate.Release(); }
    }

    public async Task<UserAccount?> ValidateAsync(string email, string password)
    {
        await _gate.WaitAsync();
        try
        {
            var accounts = await ReadAsync();
            var account = accounts.Find(item => item.Email == NormalizeEmail(email));
            // 未知帳號也做一次密碼驗證，避免快速回應直接透露帳號是否存在。
            var candidate = account ?? new UserAccount("", "", "", DummyHash, DateTimeOffset.MinValue);
            var result = _hasher.VerifyHashedPassword(candidate, candidate.PasswordHash, password);
            if (account is null || result == PasswordVerificationResult.Failed) return null;
            if (result == PasswordVerificationResult.SuccessRehashNeeded)
            {
                var updated = account with { PasswordHash = _hasher.HashPassword(account, password) };
                await SaveAsync(accounts.Select(item => item.Id == account.Id ? updated : item).ToList());
                account = updated;
            }
            return account;
        }
        finally { _gate.Release(); }
    }

    public async Task<UserAccount> GetOrCreateDevelopmentAccountAsync()
    {
        const string id = "hospital-rmf-development-account";
        const string email = "developer@localhost.invalid";

        await _gate.WaitAsync();
        try
        {
            var accounts = await ReadAsync();
            var existing = accounts.Find(account => account.Id == id);
            if (existing is not null) return existing;
            if (accounts.Any(account => account.Email == email))
                throw new InvalidOperationException("The reserved development account email is already in use.");

            var account = new UserAccount(id, email, "Development User", "", DateTimeOffset.UtcNow);
            var randomPassword = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32));
            account = account with { PasswordHash = _hasher.HashPassword(account, randomPassword) };
            await SaveAsync([.. accounts, account]);
            return account;
        }
        finally { _gate.Release(); }
    }

    public async Task<UserAccount?> UpdateProfileAsync(string id, string name, string? avatarUrl)
    {
        await _gate.WaitAsync();
        try
        {
            var accounts = await ReadAsync();
            var account = accounts.Find(item => item.Id == id);
            if (account is null) return null;
            var updated = account with { Name = name.Trim(), AvatarUrl = avatarUrl };
            await SaveAsync(accounts.Select(item => item.Id == id ? updated : item).ToList());
            return updated;
        }
        finally { _gate.Release(); }
    }

    private async Task<List<UserAccount>> ReadAsync()
    {
        if (_accounts is not null) return _accounts;
        if (!File.Exists(_path)) return _accounts = [];
        await using var stream = File.OpenRead(_path);
        return _accounts = await JsonSerializer.DeserializeAsync<List<UserAccount>>(stream)
            ?? throw new InvalidDataException("Account storage is invalid.");
    }

    private async Task SaveAsync(List<UserAccount> accounts)
    {
        var directory = Path.GetDirectoryName(_path)!;
        Directory.CreateDirectory(directory);
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(directory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        var temporary = _path + ".tmp";
        try
        {
            await using (var stream = new FileStream(temporary, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(temporary, UnixFileMode.UserRead | UnixFileMode.UserWrite);
                await JsonSerializer.SerializeAsync(stream, accounts);
                await stream.FlushAsync();
            }
            File.Move(temporary, _path, overwrite: true);
            _accounts = accounts;
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    private static string NormalizeEmail(string email) => email.Trim().ToLowerInvariant();
    private static readonly string DummyHash = new PasswordHasher<UserAccount>().HashPassword(
        new UserAccount("", "", "", "", DateTimeOffset.MinValue), Guid.NewGuid().ToString());

    public static UserProfile Profile(UserAccount account) => new(account.Id, account.Email, account.Name, account.AvatarUrl);
}
