import { useAuth } from "./AuthContext";
import Login from "./Login";
import MapView from "./MapView";

function App() {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated()) {
    return <Login />;
  }

  return <MapView />;
}

export default App;
