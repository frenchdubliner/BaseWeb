import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="page page-narrow">
      <h1>Welcome to Battleground Used Games</h1>

      {user ? (
        <div className="card">
          <p>
            You are signed in as <strong>{user.email}</strong>.
          </p>
          {!user.is_active && (
            <p className="form-hint">Your account is still pending email verification.</p>
          )}
          {user.is_active && (
            <Link className="button" to="/my-games">
              Manage your games
            </Link>
          )}
          <Link className="button button-secondary" to="/profile">
            Go to your profile
          </Link>
        </div>
      ) : (
        <div className="card">
          <Link className="button" to="/login">
            Login
          </Link>
          <Link className="button button-secondary" to="/register">
            Create an account
          </Link>
        </div>
      )}
    </div>
  );
}
