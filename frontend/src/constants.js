export const DROPOFF_LOCATIONS = [
  { value: "abington", label: "Abington" },
  { value: "norton", label: "Norton" },
  { value: "saugus", label: "Saugus" },
  { value: "framingham", label: "Framingham" },
];

export const PAYMENT_PREFERENCES = [
  { value: "store_credit_70", label: "70% of sale value in store credit" },
  { value: "cash_40", label: "40% of sale value in cash" },
];

export const GAME_CONDITIONS = [
  {
    value: "new_in_shrink",
    label: "New in Shrink",
    description: "Original shrink wrap. Never opened.",
  },
  {
    value: "like_new",
    label: "Like New",
    description: "Pieces unpunched, cards wrapped, never played.",
  },
  {
    value: "very_good",
    label: "Very Good",
    description: "Pieces punched, sorted, rarely or never played. No discernible wear.",
  },
  {
    value: "good",
    label: "Good",
    description: "Played but well maintained, pieces unsorted, box shows signs of use.",
  },
  {
    value: "fair",
    label: "Fair",
    description: "Discernible wear. Box/book show minor damage and have been slightly marked.",
  },
  {
    value: "poor",
    label: "Poor",
    description: "Worn but playable. Box/book show damage and/or have been significantly marked.",
  },
];

export const PET_EXPOSURE_OPTIONS = [
  { value: "", label: "None" },
  { value: "cat", label: "Cat" },
  { value: "dog", label: "Dog" },
  { value: "multiple", label: "Multiple pets" },
];

export function extractErrorMessage(error) {
  const data = error?.response?.data;
  if (!data) return "Something went wrong. Please try again.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const firstKey = Object.keys(data)[0];
  if (firstKey) {
    const value = data[firstKey];
    return Array.isArray(value) ? value[0] : String(value);
  }
  return "Something went wrong. Please try again.";
}

/**
 * Like extractErrorMessage, but for requests made with responseType:
 * "blob" - axios can't auto-parse an error body in that mode, so a JSON
 * error response arrives as an opaque Blob instead of a parsed object.
 */
export async function extractBlobErrorMessage(error) {
  const data = error?.response?.data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text);
      return parsed.detail || text;
    } catch {
      return "Something went wrong. Please try again.";
    }
  }
  return extractErrorMessage(error);
}
