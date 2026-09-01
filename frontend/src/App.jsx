import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ListTickets from "./pages/ListTickets";
import CreateTicket from "./pages/CreateTicket";
import DetailTicket from "./pages/DetailTicket";
import PrivateRoute from "./components/PrivateRoute";
import ManageCategories from "./pages/ManageCategories";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />}></Route>
      <Route path="/register" element={<Register />}></Route>
      <Route
        path="/tickets"
        element={
          <PrivateRoute>
            <ListTickets />
          </PrivateRoute>
        }
      />
      <Route
        path="/tickets/new"
        element={
          <PrivateRoute>
            <CreateTicket />
          </PrivateRoute>
        }
      />
      <Route
        path="/tickets/:id"
        element={
          <PrivateRoute>
            <DetailTicket />
          </PrivateRoute>
        }
      />
      <Route
        path="/admin/categories"
        element={
          <PrivateRoute permittedRoles={["admin"]}>
            <ManageCategories />
          </PrivateRoute>
        }
      />
      <Route path="/" element={<Navigate to="/tickets" replace />} />
    </Routes>
  );
}

export default App;
