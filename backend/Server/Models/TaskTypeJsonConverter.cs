using System.Text.Json;
using System.Text.Json.Serialization;

namespace Server.Models;

public sealed class TaskTypeJsonConverter : JsonConverter<TaskType>
{
    public override TaskType Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        => reader.GetString() switch
        {
            "waste_transport" => TaskType.WasteTransport,
            "clothes_collection" => TaskType.ClothesCollection,
            "medication_delivery" => TaskType.MedicationDelivery,
            "specimen_delivery" => TaskType.SpecimenDelivery,
            "ward_service" => TaskType.WardService,
            _ => throw new JsonException("Unknown task type."),
        };

    public override void Write(Utf8JsonWriter writer, TaskType value, JsonSerializerOptions options)
        => writer.WriteStringValue(value switch
        {
            TaskType.WasteTransport => "waste_transport",
            TaskType.ClothesCollection => "clothes_collection",
            TaskType.MedicationDelivery => "medication_delivery",
            TaskType.SpecimenDelivery => "specimen_delivery",
            TaskType.WardService => "ward_service",
            _ => throw new JsonException("Unknown task type."),
        });
}
