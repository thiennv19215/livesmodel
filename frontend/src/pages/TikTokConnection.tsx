import React, { useState, useEffect } from 'react';
import { Video, Power, CheckCircle2, RefreshCw } from 'lucide-react';
import axios from 'axios';

export const TikTokConnection: React.FC = () => {
  const [username, setUsername] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [activeUsername, setActiveUsername] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get('/api/tiktok/status');
        setIsConnected(res.data.is_connected);
        setActiveUsername(res.data.username);
        if (res.data.username) {
          setUsername(current => current || res.data.username);
        }
      } catch (err) {
        console.error(err);
      }
    };

    void fetchStatus();
    const statusTimer = setInterval(() => void fetchStatus(), 3000);
    return () => clearInterval(statusTimer);
  }, []);

  const handleConnect = async (useMock: boolean = false) => {
    setLoading(true);
    const targetUser = useMock ? 'mock_simulation_room' : username;
    try {
      const res = await axios.post('/api/tiktok/connect', { username: targetUser });
      setIsConnected(res.data.status === 'connected');
      setActiveUsername(targetUser);
    } catch {
      alert('Không thể kết nối tới TikTok Live');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      await axios.post('/api/tiktok/disconnect');
      setIsConnected(false);
      setActiveUsername('');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-panel" style={{ padding: '32px' }}>
        <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <Video size={24} color="var(--accent-purple)" /> Kết Nối TikTok Live Stream
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
          Nhập Username phòng TikTok đang phát trực tiếp để tự động lắng nghe bình luận, quà tặng và thả tim.
        </p>

        {isConnected ? (
          <div style={{ padding: '24px', borderRadius: '12px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#10b981', fontWeight: 'bold', fontSize: '16px' }}>
              <CheckCircle2 size={24} /> Đang kết nối tới: @{activeUsername}
            </div>
            <p style={{ color: 'var(--text-primary)', fontSize: '14px' }}>
              Hệ thống AI Host đang sẵn sàng trả lời tự động các câu hỏi của khán giả.
            </p>
            <button onClick={handleDisconnect} className="btn-secondary" style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.4)', width: 'fit-content' }} disabled={loading}>
              <Power size={16} /> Ngắt Kết Nối
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>TikTok Username (Unique ID)</label>
              <input
                type="text"
                className="input-field"
                placeholder="Ví dụ: thiennv19215 (không cần dấu @)"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button onClick={() => handleConnect(false)} className="btn-primary" disabled={loading || !username.trim()}>
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Power size={16} />} Connect Real TikTok Live
              </button>
              <button onClick={() => handleConnect(true)} className="btn-secondary" disabled={loading}>
                Chế Độ Giả Lập (Simulation Mode)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
