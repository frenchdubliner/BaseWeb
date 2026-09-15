import { useEffect, useState } from "react";

import listingsClient from "../api/listingsClient";
import {
  DROPOFF_LOCATIONS,
  GAME_CONDITIONS,
  PET_EXPOSURE_OPTIONS,
  extractBlobErrorMessage,
  extractErrorMessage,
} from "../constants";

const emptyFilters = {
  id: "",
  email: "",
  first_name: "",
  last_name: "",
  dropoff_location: "",
  printed: "",
  received: "",
};

function conditionLabel(value) {
  return GAME_CONDITIONS.find((option) => option.value === value)?.label || value;
}

export default function AdminGames() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState(emptyFilters);
  const [appliedParams, setAppliedParams] = useState({});

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [printingAll, setPrintingAll] = useState(false);

  const loadListings = (params) => {
    setLoading(true);
    setLoadError("");
    setAppliedParams(params);
    listingsClient
      .get("/admin/", { params })
      .then(({ data }) => setListings(data))
      .catch((err) => setLoadError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadListings({});
  }, []);

  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const activeParams = (values) =>
    Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim() !== ""));

  const applyFilters = (event) => {
    event.preventDefault();
    loadListings(activeParams(filters));
  };

  const clearFilters = () => {
    setFilters(emptyFilters);
    loadListings({});
  };

  const startEdit = (listing) => {
    setEditingId(listing.id);
    setEditForm({
      game_name: listing.game_name,
      price: listing.price,
      condition: listing.condition,
      has_missing_pieces: listing.has_missing_pieces,
      missing_pieces_description: listing.missing_pieces_description,
      smoking_household: listing.smoking_household,
      musty_smell: listing.musty_smell,
      pet_exposure: listing.pet_exposure,
      comments: listing.comments,
    });
    setFormError("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm(null);
    setFormError("");
  };

  const handleEditChange = (event) => {
    const { name, value, type, checked } = event.target;
    setEditForm((prev) => {
      const next = { ...prev, [name]: type === "checkbox" ? checked : value };
      if (name === "has_missing_pieces" && !checked) {
        next.missing_pieces_description = "";
      }
      return next;
    });
  };

  const saveEdit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const { data } = await listingsClient.patch(`/admin/${editingId}/`, editForm);
      setListings((prev) => prev.map((item) => (item.id === editingId ? data : item)));
      cancelEdit();
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this listing? This cannot be undone.")) return;
    try {
      await listingsClient.delete(`/admin/${id}/`);
      setListings((prev) => prev.filter((item) => item.id !== id));
      if (editingId === id) cancelEdit();
    } catch (err) {
      setLoadError(extractErrorMessage(err));
    }
  };

  const handlePrint = async (id) => {
    setLoadError("");
    try {
      const response = await listingsClient.get(`/admin/${id}/print/`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `game-${id}-price-tag.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      // Reflect the now-printed status immediately - no page reload needed.
      setListings((prev) => prev.map((item) => (item.id === id ? { ...item, printed: true } : item)));
    } catch (err) {
      setLoadError(extractErrorMessage(err));
    }
  };

  const handleToggleReceived = async (listing) => {
    setLoadError("");
    try {
      const { data } = await listingsClient.patch(`/admin/${listing.id}/`, {
        received: !listing.received,
      });
      setListings((prev) => prev.map((item) => (item.id === listing.id ? data : item)));
    } catch (err) {
      setLoadError(extractErrorMessage(err));
    }
  };

  const handlePrintAll = async () => {
    setLoadError("");
    setPrintingAll(true);
    try {
      const response = await listingsClient.get("/admin/print-all/", {
        params: appliedParams,
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "price-tags.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      // print-all covers every currently-listed (filtered) game - reflect
      // that immediately rather than waiting on a reload.
      setListings((prev) => prev.map((item) => ({ ...item, printed: true })));
    } catch (err) {
      setLoadError(await extractBlobErrorMessage(err));
    } finally {
      setPrintingAll(false);
    }
  };

  return (
    <div className="page page-wide">
      <h1>All Games</h1>

      <div>
        <button
          type="button"
          className="button button-secondary"
          onClick={() => setShowFilters((prev) => !prev)}
        >
          🔍 Filter
        </button>
        <button
          type="button"
          className="button button-secondary"
          onClick={handlePrintAll}
          disabled={printingAll || loading || listings.length === 0}
        >
          {printingAll ? "Preparing PDF..." : "🖨️ Print all filtered"}
        </button>
      </div>

      {showFilters && (
        <form className="form filter-form" onSubmit={applyFilters}>
          <label>
            Game ID
            <input type="text" name="id" value={filters.id} onChange={handleFilterChange} />
          </label>
          <label>
            User email
            <input type="text" name="email" value={filters.email} onChange={handleFilterChange} />
          </label>
          <label>
            First name
            <input
              type="text"
              name="first_name"
              value={filters.first_name}
              onChange={handleFilterChange}
            />
          </label>
          <label>
            Last name
            <input
              type="text"
              name="last_name"
              value={filters.last_name}
              onChange={handleFilterChange}
            />
          </label>
          <label>
            Dropoff location
            <select name="dropoff_location" value={filters.dropoff_location} onChange={handleFilterChange}>
              <option value="">Any</option>
              {DROPOFF_LOCATIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Printed
            <select name="printed" value={filters.printed} onChange={handleFilterChange}>
              <option value="">Any</option>
              <option value="true">Printed</option>
              <option value="false">Not printed</option>
            </select>
          </label>
          <label>
            Received
            <select name="received" value={filters.received} onChange={handleFilterChange}>
              <option value="">Any</option>
              <option value="true">Received</option>
              <option value="false">Not received</option>
            </select>
          </label>
          <div>
            <button type="submit" className="button">
              Apply filters
            </button>
            <button type="button" className="button button-secondary" onClick={clearFilters}>
              Clear filters
            </button>
          </div>
        </form>
      )}

      {loading && <p className="page-loading">Loading...</p>}
      {loadError && <p className="form-error">{loadError}</p>}

      {editingId && editForm && (
        <form className="form" onSubmit={saveEdit}>
          <h2>Edit game #{editingId}</h2>
          <label>
            Game name
            <input
              type="text"
              name="game_name"
              value={editForm.game_name}
              onChange={handleEditChange}
            />
          </label>
          <label>
            Price ($)
            <input
              type="number"
              name="price"
              min="0"
              step="0.01"
              value={editForm.price}
              onChange={handleEditChange}
            />
          </label>
          <label>
            Condition
            <select name="condition" value={editForm.condition} onChange={handleEditChange}>
              {GAME_CONDITIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              name="has_missing_pieces"
              checked={editForm.has_missing_pieces}
              onChange={handleEditChange}
            />
            Has missing pieces?
          </label>
          {editForm.has_missing_pieces && (
            <label>
              Which piece(s) are missing?
              <input
                type="text"
                name="missing_pieces_description"
                maxLength={64}
                value={editForm.missing_pieces_description}
                onChange={handleEditChange}
              />
            </label>
          )}

          <label className="checkbox-label">
            <input
              type="checkbox"
              name="smoking_household"
              checked={editForm.smoking_household}
              onChange={handleEditChange}
            />
            Exposed to smoking household?
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              name="musty_smell"
              checked={editForm.musty_smell}
              onChange={handleEditChange}
            />
            Has musty smell?
          </label>

          <label>
            Pet exposure
            <select name="pet_exposure" value={editForm.pet_exposure} onChange={handleEditChange}>
              {PET_EXPOSURE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Comments
            <input
              type="text"
              name="comments"
              maxLength={64}
              value={editForm.comments}
              onChange={handleEditChange}
            />
          </label>

          {formError && <p className="form-error">{formError}</p>}

          <div>
            <button type="submit" className="button" disabled={saving}>
              {saving ? "Saving..." : "Save changes"}
            </button>
            <button type="button" className="button button-secondary" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Game</th>
              <th>Price</th>
              <th>Condition</th>
              <th>Owner</th>
              <th>Printed</th>
              <th className="admin-table-actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((listing) => (
              <tr key={listing.id}>
                <td>
                  {listing.game_name}
                  <br />
                  <span className="form-hint">#{listing.id}</span>
                </td>
                <td>${Number(listing.price).toFixed(2)}</td>
                <td>{conditionLabel(listing.condition)}</td>
                <td>
                  {listing.owner_first_name} {listing.owner_last_name}
                  <br />
                  <span className="form-hint">
                    {listing.owner_email} · {listing.owner_dropoff_location}
                  </span>
                </td>
                <td>{listing.printed ? "Yes" : "No"}</td>
                <td className="admin-table-actions-col">
                  <div className="admin-table-actions">
                    <button
                      type="button"
                      className={listing.received ? "button-sm button-secondary" : "button-sm"}
                      onClick={() => handleToggleReceived(listing)}
                    >
                      {listing.received ? "Received" : "Not Received"}
                    </button>
                    <button type="button" className="button-sm" onClick={() => startEdit(listing)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button-sm button-secondary"
                      onClick={() => handlePrint(listing.id)}
                    >
                      Print
                    </button>
                    <button
                      type="button"
                      className="button-sm button-secondary"
                      onClick={() => handleDelete(listing.id)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && listings.length === 0 && (
              <tr>
                <td colSpan={6}>No games match these filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
