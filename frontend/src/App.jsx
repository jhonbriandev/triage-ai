import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ListTickets from "./pages/ListTickets";
import PrivateRoute from "./components/PrivateRoute";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />}></Route>
      <Route path="/register" element={<Register />} />
      <Route
        path="/tickets"
        element={
          <PrivateRoute>
            <ListTickets />
          </PrivateRoute>
        }
      />
      <Route path="/" element={<Navigate to="/tickets" replace />} />
    </Routes>
  );
}

export default App;
