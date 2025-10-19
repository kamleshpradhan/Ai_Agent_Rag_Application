import React, { useState, useEffect, useRef, useCallback } from 'react';

export default function Agent() {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isConnected, setIsConnected] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const ws = useRef(null);
    const messagesEndRef = useRef(null);
    const currentAIMessageRef = useRef('');

    // ✅ FIX: Memoized message handler to prevent duplicates
    const handleWebSocketMessage = useCallback((event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'typing':
                setIsTyping(true);
                currentAIMessageRef.current = ''; // Reset current AI message
                break;

            case 'stream':
                setMessages(prev => {
                    const newMessages = [...prev];
                    const lastMessage = newMessages[newMessages.length - 1];

                    if (lastMessage && lastMessage.sender === 'ai' && lastMessage.streaming) {
                        // ✅ FIX: Replace content instead of appending if full_content exists
                        if (data.full_content) {
                            lastMessage.content = data.full_content;
                            currentAIMessageRef.current = data.full_content;
                        } else {
                            // Only append if it's new content
                            if (!currentAIMessageRef.current.includes(data.content)) {
                                lastMessage.content += data.content;
                                currentAIMessageRef.current += data.content;
                            }
                        }
                    } else {
                        // Create new AI message
                        const newContent = data.full_content || data.content || '';
                        currentAIMessageRef.current = newContent;
                        newMessages.push({
                            id: `ai-${Date.now()}-${Math.random()}`,
                            sender: 'ai',
                            content: newContent,
                            streaming: true
                        });
                    }
                    return newMessages;
                });
                break;

            case 'complete':
                setIsTyping(false);
                setMessages(prev =>
                    prev.map(msg => {
                        if (msg.streaming) {
                            return { 
                                ...msg, 
                                streaming: false,
                                content: data.full_response || msg.content // Use final response if available
                            };
                        }
                        return msg;
                    })
                );
                currentAIMessageRef.current = '';
                break;

            case 'error':
                setIsTyping(false);
                setMessages(prev => [...prev, {
                    id: `error-${Date.now()}`,
                    sender: 'system',
                    content: `Error: ${data.message}`,
                    streaming: false
                }]);
                currentAIMessageRef.current = '';
                break;
        }
    }, []);

    useEffect(() => {
        // Connect to WebSocket
        ws.current = new WebSocket('ws://localhost:8000/ws/chat');

        ws.current.onopen = () => {
            setIsConnected(true);
            console.log('Connected to WebSocket');
        };

        ws.current.onmessage = handleWebSocketMessage;

        ws.current.onclose = () => {
            setIsConnected(false);
            setIsTyping(false);
            console.log('Disconnected from WebSocket');
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket error:', error);
            setIsConnected(false);
            setIsTyping(false);
        };

        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [handleWebSocketMessage]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = useCallback(() => {
        const trimmedMessage = inputMessage.trim();
        if (trimmedMessage && isConnected) {
            // Add user message to UI
            setMessages(prev => [...prev, {
                id: `user-${Date.now()}`,
                sender: 'user',
                content: trimmedMessage,
                streaming: false
            }]);

            // Send to WebSocket
            ws.current.send(JSON.stringify({
                message: trimmedMessage
            }));

            setInputMessage('');
        }
    }, [inputMessage, isConnected]);

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // ✅ FIX: Clear chat function
    const clearChat = () => {
        setMessages([]);
        currentAIMessageRef.current = '';
    };

    return (
        <div style={{ maxWidth: '600px', margin: '0 auto', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h2>AI Chat</h2>
                <button 
                    onClick={clearChat}
                    style={{ 
                        padding: '5px 10px',
                        backgroundColor: '#f44336',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                    }}
                >
                    Clear Chat
                </button>
            </div>
            
            <div style={{
                border: '1px solid #ccc',
                height: '400px',
                overflowY: 'scroll',
                padding: '10px',
                marginBottom: '10px',
                backgroundColor: '#f9f9f9'
            }}>
                {messages.length === 0 && (
                    <div style={{ color: '#666', fontStyle: 'italic', textAlign: 'center', marginTop: '20px' }}>
                        Start a conversation with the AI...
                    </div>
                )}
                
                {messages.map(message => (
                    <div key={message.id} style={{
                        marginBottom: '10px',
                        padding: '8px',
                        borderRadius: '8px',
                        maxWidth: '80%',
                        marginLeft: message.sender === 'user' ? 'auto' : '0',
                        marginRight: message.sender === 'user' ? '0' : 'auto',
                        backgroundColor: message.sender === 'user' ? '#2196f3' : 
                                       message.sender === 'ai' ? '#4caf50' : '#ff9800',
                        color: 'white'
                    }}>
                        <div style={{ fontSize: '12px', opacity: 0.8, marginBottom: '4px' }}>
                            {message.sender === 'user' ? 'You' : 
                             message.sender === 'ai' ? 'AI' : 'System'}
                        </div>
                        <div>{message.content}</div>
                        {message.streaming && <span style={{ opacity: 0.7 }}> ▋</span>}
                    </div>
                ))}
                
                {isTyping && (
                    <div style={{ 
                        color: '#666', 
                        fontStyle: 'italic',
                        padding: '8px',
                        backgroundColor: '#fff3e0',
                        borderRadius: '4px',
                        marginBottom: '10px'
                    }}>
                        AI is thinking...
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
                <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your message..."
                    style={{ 
                        flex: 1, 
                        padding: '10px',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        fontSize: '14px'
                    }}
                    disabled={!isConnected}
                />
                <button
                    onClick={sendMessage}
                    disabled={!isConnected || !inputMessage.trim() || isTyping}
                    style={{ 
                        padding: '10px 20px',
                        backgroundColor: isConnected && inputMessage.trim() && !isTyping ? '#2196f3' : '#ccc',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: isConnected && inputMessage.trim() && !isTyping ? 'pointer' : 'not-allowed',
                        minWidth: '80px'
                    }}
                >
                    {isTyping ? '...' : 'Send'}
                </button>
            </div>

            <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
                Status: <span style={{ color: isConnected ? '#4caf50' : '#f44336', fontWeight: 'bold' }}>
                    {isConnected ? '● Connected' : '● Disconnected'}
                </span>
                {messages.length > 0 && (
                    <span style={{ marginLeft: '20px' }}>
                        Messages: {messages.length}
                    </span>
                )}
            </div>
        </div>
    );
}
