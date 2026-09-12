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
