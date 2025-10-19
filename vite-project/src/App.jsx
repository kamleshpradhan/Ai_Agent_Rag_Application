import Nav from "./components/nav"
import Home from "./components/home"
import Login from "./components/login"
import SignUp from "./components/signup"
import Agent from "./components/agent"
import { Routes, Route } from "react-router-dom"
import { useState, useEffect } from "react"
import ProtectedRoute from "./components/protectedRoute"
export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check authentication status (token, API call, etc.)
    const token = localStorage.getItem('authToken');
    token ? setIsAuthenticated(!isAuthenticated) : setIsAuthenticated(isAuthenticated);
  }, []);

  return (
    <div>
      <Nav />
      <Routes>
        <Route path="" element={<ProtectedRoute isAuthenticated={isAuthenticated}>
          <Home />
        </ProtectedRoute>}></Route>
        <Route path="/agent" element={<ProtectedRoute isAuthenticated={isAuthenticated}>
          <Agent />
        </ProtectedRoute>}></Route>
        <Route path="/login" element={<Login />}></Route>
        <Route path="/signup" element={<SignUp />}></Route>
      </Routes>
    </div>
  )
}