import { useState, useRef, useEffect } from "react";
import styles from "../../styles/nav.module.css";
import { useNavigate } from "react-router-dom";

export default function Nav({ items = ["Home", "Agent", "Docs", "Settings"] }) {
    const [active, setActive] = useState(0);
    const containerRef = useRef(null);
    const indicatorRef = useRef(null);
    const itemRefs = useRef([]);
    const navigate  = useNavigate();

    useEffect(() => {
        // ensure refs array matches items length
        itemRefs.current = itemRefs.current.slice(0, items.length);

        const currentEl = itemRefs.current[active];
        const containerEl = containerRef.current;
        const indicatorEl = indicatorRef.current;
        if (!currentEl || !containerEl || !indicatorEl) return;

        const containerRect = containerEl.getBoundingClientRect();
        const itemRect = currentEl.getBoundingClientRect();

        const left = itemRect.left - containerRect.left;
        const width = itemRect.width;

        // Apply styles to the indicator (animated)
        indicatorEl.style.transform = `translateX(${left}px)`;
        indicatorEl.style.width = `${width}px`;
    }, [active, items]);



    function handleClick(i){
        setActive(i)
         if(items[i] == "Home"){
            navigate("")
         }
          if(items[i] == "Agent"){
            navigate("/agent")
         }
          if(items[i] == "Docs"){
            navigate("/login")
         }
          if(items[i] == "Settings"){
            navigate("/signup")
         }

    }
    return (
        <nav className={styles.nav} aria-label="Main navigation">
            <div className={styles.brand}>
                <div className={styles.logo} />
                <span className={styles.title}>My App</span>
            </div>

            <div className={styles.items} ref={containerRef} role="tablist">
                {items.map((label, i) => (
                    <button
                        key={label}
                        ref={(el) => (itemRefs.current[i] = el)}
                        className={`${styles.item} ${i === active ? styles.active : ""}`}
                        onClick={() => handleClick(i)}
                        role="tab"
                        aria-selected={i === active}
                    >
                        {label}
                    </button>
                ))}
                <span className={styles.indicator} ref={indicatorRef} aria-hidden="true" />
            </div>
        </nav>
    );
}