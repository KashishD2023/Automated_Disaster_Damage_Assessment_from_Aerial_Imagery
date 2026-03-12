import { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import "./UserHistory.css";

function UserHistory() {
  const { user, getAuthHeaders } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    fetchUserHistory();
  }, []);

  const fetchUserHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/history`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch history");
      }

      const data = await response.json();
      setHistory(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="history-container">Loading history...</div>;
  }

  if (error) {
    return <div className="history-container error">Error: {error}</div>;
  }

  return (
    <div className="history-container">
      <h3>Analysis History for {user?.username}</h3>
      
      {history.length === 0 ? (
        <p className="no-history">No tile analysis history found.</p>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <div key={item.id} className="history-item">
              <div className="history-tile">Tile: {item.tile_id}</div>
              <div className="history-mode">View: {item.view_mode.toUpperCase()}</div>
              <div className="history-time">
                {new Date(item.analyzed_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default UserHistory;
