import { useState } from "react";
import styles from "../../styles/login.module.css";
import { useNavigate } from "react-router";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function Login({ onLogin }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    async function submit(e) {
        e.preventDefault();
        setError(null);
        if (!email || !password) { setError('Email and password required'); return; }
        setLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: email, password })
            });
            const data = await resp.json();

            if (!resp.ok) throw new Error(data.detail || 'Login failed');
            navigate('/signup', { replace: true });
            if (resp.ok) {
                localStorage.setItem("authToken", JSON.stringify(`Bearer ${data.token}`))
                navigate("/",{replace:true})
            }
        } catch (err) {
            setError(err.message || String(err));
        } finally { setLoading(false); }
    }

    return (
        <div className={styles.wrap}>
            <form className={styles.form} onSubmit={submit}>
                <h2>Log in</h2>
                {error && <div className={styles.error}>{error}</div>}
                <label>
                    Email
                    <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
                </label>
                <label>
                    Password
                    <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
                </label>
                <button type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
            </form>
        </div>
    )
}