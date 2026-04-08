import type { Metadata } from "../types";

const FIELDS: Array<keyof Metadata> = [
  "catalogNumber",
  "recordNumber",
  "family",
  "scientificName",
  "scientificNameAuthorship",
  "eventDate",
  "country",
  "stateProvince",
  "County",
  "Locality",
  "decimalLatitude",
  "decimalLongitude",
  "recordedBy",
  "associatedCollectors",
  "minimumElevationInMeters",
];

function displayValue(v: Metadata[keyof Metadata]): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.length === 0 ? "—" : v.join(", ");
  return String(v);
}

export function MetadataPanel({ metadata }: { metadata: Metadata | null }) {
  if (!metadata) return <p className="text-gray-400 text-sm">No metadata yet.</p>;

  return (
    <div className="space-y-1">
      {FIELDS.map((key) => (
        <div key={key} className="flex gap-2 text-sm">
          <span className="text-gray-500 w-44 shrink-0">{key}</span>
          <span className="text-gray-900 break-words">{displayValue(metadata[key])}</span>
        </div>
      ))}
    </div>
  );
}
