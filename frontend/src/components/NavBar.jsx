import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        Battleground Used Games
      </Link>
      <div className="navbar-links">
        {user ? (
          <>
            {user.is_active && <Link to="/my-games">My Games</Link>}
            {user.is_staff && <Link to="/admin/users">Users</Link>}
            {user.is_staff && <Link to="/admin/games">Games</Link>}
            {user.is_staff && <Link to="/admin/convention">Convention</Link>}
            <Link to="/profile">Profile</Link>
            <button type="button" className="link-button" onClick={handleLogout}>
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
