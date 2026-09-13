import { createApiClient } from "./createClient";

export { clearTokens, getTokens, setTokens } from "./tokens";

const client = createApiClient("/api/auth");

export default client;
