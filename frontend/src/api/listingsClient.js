import { createApiClient } from "./createClient";

const listingsClient = createApiClient("/api/listings");

export default listingsClient;
