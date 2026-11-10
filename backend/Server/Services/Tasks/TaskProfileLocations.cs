using Server.Models;

namespace Server.Services.Tasks;

// Mirrors the allowed stations in task_profiles.yaml until profiles are loaded from shared configuration.
public static class TaskProfileLocations
{
    private static readonly HashSet<string> WardSources = ["ward_a_2", "ward_b_2", "consult_1_2", "consult_2_2", "consult_3_2"];
    private static readonly HashSet<string> CleanExtras = ["x-ray", "ultrasound_2", "ecg_2", "therapy_room"];

    public static bool IsAllowed(TaskType type, string? source, string? destination)
    {
        if (string.IsNullOrWhiteSpace(source) || string.IsNullOrWhiteSpace(destination)) return false;
        return type switch
        {
            TaskType.WasteTransport => destination == "waste_return_2" &&
                (WardSources.Contains(source) || CleanExtras.Contains(source) || source is "nurse_station" or "blood_draw"),
            TaskType.ClothesCollection => destination == "clothes_return_2" &&
                (source is "ward_a_2" or "ward_b_2" || CleanExtras.Contains(source)),
            TaskType.MedicationDelivery => source == "pharmacy" &&
                (WardSources.Contains(destination) || destination == "nurse_station"),
            TaskType.SpecimenDelivery => destination == "lab" &&
                (WardSources.Contains(source) || source == "blood_draw"),
            TaskType.WardService => source == "nurse_station" &&
                (destination is "ward_a_2" or "ward_b_2"),
            _ => false,
        };
    }
}
