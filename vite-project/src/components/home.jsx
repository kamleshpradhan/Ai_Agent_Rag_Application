import { useEffect, useState } from "react";
import Nav from "./nav";
import styles from "../../styles/home.module.css";
import { redirect } from "react-router";
import { useNavigate } from "react-router";

export default function Home() {
  const [files, setFiles] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchFiles();
  }, []);



  function getAuthToken() {
    const resp = localStorage.getItem("authToken")
    return resp
  }


  async function fetchFiles() {
    try {
      const resp = await fetch("http://localhost:8000/api/documents", {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': JSON.parse(getAuthToken())
        }
      });
      const data = await resp.json();
      if (data) {
        setFiles(data)
      }else{
        setFiles([])
      }
    } catch (e) {
      console.error(e)
    }
  }

  async function handleUpload(e) {
    const f = e.target.files[0];
    if (!f) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", f);
    try {
      const resp = await fetch("http://localhost:8000/api/documents/upload", {
        method: "POST",
        headers: {
          'Authorization': JSON.parse(getAuthToken()),
        }, body: form
      });
      if (resp.ok) {
        window.alert("File Uploaded")
      }
      if (!resp.ok) throw new Error("Upload failed");
      await fetchFiles();
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  }

  async function fetchChats(doc_id) {
    const resp = await fetch(`http://localhost:8000/api/chat/${doc_id}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": JSON.parse(getAuthToken())
      },
    });
    return resp
  }
  async function deleteFile(e, id) {
    // prevent the card's onClick selecting the document
    e.stopPropagation();
    try {
      const resp = await fetch(`http://localhost:8000/api/documents/${id}`,
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            "Authorization": JSON.parse(getAuthToken())
          }
        });
      if (!resp.ok) throw new Error('Delete failed');
      // refresh file list and clear selection if we deleted the selected doc
      await fetchFiles();
      if (selectedDoc && selectedDoc.doc_id === id) setSelectedDoc(null);
    } catch (err) {
      console.log(err)
    }
  }

  async function sendMessage() {
    if (!selectedDoc || !message.trim()) return;
    const docId = selectedDoc.document_id;
    const payload = { role: "user", text: message };
    try {
      const resp = await fetch(`http://localhost:8000/api/chat/${docId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": JSON.parse(getAuthToken())
        },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (resp) {
        try {
          const chatsResp = await fetchChats(docId);
          const datsa = await chatsResp.json();
          if (Array.isArray(datsa.messages) && datsa.messages.length > 0) {
            // Convert each stored record into two message objects (user then assistant)
            const newMessages = datsa.messages.flatMap((rec) => [
              { role: "user", text: rec.user_message },
              { role: "assistant", text: rec.ai_response },
            ]);
            setMessages((prev) => [...prev, ...newMessages]);
            setMessage("");
          }
        } catch (err) {
          console.log("fetching data error", err);
        }
      }
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className={styles.page}>
      <main className={styles.container}>
        <section className={styles.uploadSection}>
          <label className={styles.uploadLabel}>
            <input type="file" accept=".txt,.pdf" onChange={handleUpload} disabled={uploading} />
            <span>{uploading ? "Uploading..." : "Choose file to upload"}</span>
          </label>
        </section>

        <section className={styles.gridSection}>
          <h3>Uploaded Files</h3>
          <div className={styles.grid}>
            {files.length === 0 && <div className={styles.empty}>No files uploaded</div>}
            {files.length>0 ? files.map((f) => (
              <div
                key={f.id}
                className={`${styles.card} ${selectedDoc && selectedDoc.id === f.id ? styles.selected : ""}`}
                onClick={() => setSelectedDoc(f)}
              >

                <div className={styles.filename}>{f.filename}</div>
                {/* <div className={styles.meta}>{f.doc_id==selectedDoc.d}</div> */}
                <button onClick={(e) => deleteFile(e, f.document_id)}
                  value={f.document_id}>🗑️</button>
              </div>
            )): <div></div>}
          </div>
        </section>

        <section className={styles.chatSection}>
          <h3>Chat</h3>
          <div className={styles.chatBox}>
            {selectedDoc ? (
              <>
                <div className={styles.chatMessages}>
                  {messages.map((m, i) => (
                    <div key={i} className={m.role === "assistant" ? styles.assistant : styles.user}>
                      <strong>{m.role}</strong>: {m.text}
                    </div>
                  ))}
                </div>

                <div className={styles.chatInputRow}>
                  <input
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder={`Message about ${selectedDoc.name}...`}
                  />
                  <button onClick={sendMessage} className={styles.sendBtn}>
                    Send
                  </button>
                </div>
              </>
            ) : (
              <div className={styles.noSelect}>Select a document to enable chat</div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
