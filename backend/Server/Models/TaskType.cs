using System.Text.Json.Serialization;

namespace Server.Models;

[JsonConverter(typeof(TaskTypeJsonConverter))]
public enum TaskType
{
    WasteTransport,
    ClothesCollection,
    MedicationDelivery,
    SpecimenDelivery,
    WardService
}
