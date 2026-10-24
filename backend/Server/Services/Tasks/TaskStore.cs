using System.Collections.Concurrent;
using System.Diagnostics.CodeAnalysis;
using Server.Models;

namespace Server.Services.Tasks;

// Registered as a singleton in Program.cs and shared by task services and the scheduler.
// Tasks and task codes remain in memory only until the server stops.
public sealed class TaskStore : IDisposable
{
    // Store RobotTask objects by their internal task ID.
    private readonly ConcurrentDictionary<string, RobotTask> _tasks = new();

    // Track the sequence used to generate readable task codes.
    private long _taskSequence;

    // TaskService uses this gate to prevent editing or deleting during dispatch.
    internal SemaphoreSlim DispatchGate { get; } = new(1, 1);

    // Return a list of the currently stored task objects.
    public List<RobotTask> GetAll()
    {
        return _tasks.Values.ToList();
    }

    // Return whether the ID exists and provide its task through the out parameter.
    public bool TryGet(string id, [NotNullWhen(true)] out RobotTask? task)
    {
        return _tasks.TryGetValue(id, out task);
    }

    // Store a task using its internal ID as the dictionary key.
    public void Add(RobotTask task)
    {
        _tasks[task.Id] = task;
    }

    // Remove a task by ID and return whether an entry was removed.
    public bool Remove(string id)
    {
        return _tasks.TryRemove(id, out _);
    }

    // Generate a code such as T0001 using an atomic counter for concurrent requests.
    public string NextTaskCode()
    {
        return $"T{Interlocked.Increment(ref _taskSequence):D4}";
    }

    // Release the semaphore when the application disposes this store.
    public void Dispose()
    {
        DispatchGate.Dispose();
    }
}
