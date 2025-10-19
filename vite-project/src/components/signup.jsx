import { useState } from "react";
import {useNavigate} from "react-router-dom"
import styles from "../../styles/signup.module.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function SignUp({ onSignup }){
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate()

    async function submit(e){
        e.preventDefault();
        setError(null);
        if(!username || !email || !password){ setError('All fields are required'); return; }
        setLoading(true);
        try{
            const resp = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            const data = await resp.json();
            if(!resp.ok) throw new Error(data.detail || 'Signup failed');
             navigate('/login', { replace: true });
        }catch(err){ setError(err.message || String(err)); }
        finally{ setLoading(false); }
    }

    return (
        <div className={styles.wrap}>
            <form className={styles.form} onSubmit={submit}>
                <h2>Create account</h2>
                {error && <div className={styles.error}>{error}</div>}
                <label>
                    Username
                    <input value={username} onChange={(e)=>setUsername(e.target.value)} type="text" />
                </label>
                <label>
                    Email
                    <input value={email} onChange={(e)=>setEmail(e.target.value)} type="email" />
                </label>
                <label>
                    Password
                    <input value={password} onChange={(e)=>setPassword(e.target.value)} type="password" />
                </label>
                <button type="submit" disabled={loading}>{loading ? 'Creating...' : 'Sign up'}</button>
            </form>
        </div>
    )
}