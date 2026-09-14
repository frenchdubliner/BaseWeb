import { useEffect, useState } from "react";

import client from "../api/client";
import { DROPOFF_LOCATIONS, PAYMENT_PREFERENCES, extractErrorMessage } from "../constants";

const emptyFilters = { email: "", first_name: "", last_name: "", phone_number: "" };

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState(emptyFilters);

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const loadUsers = (params) => {
    setLoading(true);
    setLoadError("");
    client
      .get("/admin/users/", { params })
      .then(({ data }) => setUsers(data))
      .catch((err) => setLoadError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUsers({});
  }, []);

  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const activeParams = (values) =>
    Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim() !== ""));

  const applyFilters = (event) => {
    event.preventDefault();
    loadUsers(activeParams(filters));
  };

  const clearFilters = () => {
    setFilters(emptyFilters);
    loadUsers({});
  };

  const startEdit = (user) => {
    setEditingId(user.id);
    setEditForm({
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      phone_number: user.phone_number,
      dropoff_location: user.dropoff_location,
      payment_preference: user.payment_preference,
      is_active: user.is_active,
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
    setEditForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const saveEdit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const { data } = await client.patch(`/admin/users/${editingId}/`, editForm);
      setUsers((prev) => prev.map((u) => (u.id === editingId ? data : u)));
      cancelEdit();
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page page-wide">
      <h1>All Users</h1>

      <div>
        <button
          type="button"
          className="button button-secondary"
          onClick={() => setShowFilters((prev) => !prev)}
        >
          🔍 Filter
        </button>
      </div>

      {showFilters && (
        <form className="form filter-form" onSubmit={applyFilters}>
          <label>
            Email
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
            Phone number
            <input
              type="text"
              name="phone_number"
              value={filters.phone_number}
              onChange={handleFilterChange}
            />
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
          <h2>Edit user</h2>
          <label>
            Email
            <input type="email" name="email" value={editForm.email} onChange={handleEditChange} />
          </label>
          <label>
            First name
            <input
              type="text"
              name="first_name"
              value={editForm.first_name}
              onChange={handleEditChange}
            />
          </label>
          <label>
            Last name
            <input
              type="text"
              name="last_name"
              value={editForm.last_name}
              onChange={handleEditChange}
            />
          </label>
          <label>
            Phone number
            <input
              type="tel"
              name="phone_number"
              value={editForm.phone_number}
              onChange={handleEditChange}
            />
          </label>
          <label>
            Dropoff location
            <select name="dropoff_location" value={editForm.dropoff_location} onChange={handleEditChange}>
              {DROPOFF_LOCATIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Payment preference
            <select
              name="payment_preference"
              value={editForm.payment_preference}
              onChange={handleEditChange}
            >
              {PAYMENT_PREFERENCES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="is_active"
              checked={editForm.is_active}
              onChange={handleEditChange}
            />
            Email verified (active)
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
              <th>Email</th>
              <th>First name</th>
              <th>Last name</th>
              <th>Phone</th>
              <th>Dropoff</th>
              <th>Verified</th>
              <th>Staff</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{user.first_name}</td>
                <td>{user.last_name}</td>
                <td>{user.phone_number}</td>
                <td>{user.dropoff_location}</td>
                <td>{user.is_active ? "Yes" : "No"}</td>
                <td>{user.is_staff ? "Yes" : "No"}</td>
                <td>
                  <button type="button" className="button" onClick={() => startEdit(user)}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={8}>No users match these filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
