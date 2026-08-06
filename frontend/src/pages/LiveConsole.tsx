import React, { useState, useEffect } from 'react';
import { MessageSquare, Send, Sparkles, Volume2, ShoppingBag } from 'lucide-react';
import axios from 'axios';

interface LiveEvent {
  user_name: string;
  comment?: string;
  ai_reply?: string;
  matched_product?: string;
  type: string;
}

export const LiveConsole: React.FC = () => {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [manualUser, setManualUser] = useState('Khán Giả Demo');
  const [manualComment, setManualComment] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [activeRoom, setActiveRoom] = useState('');

  useEffect(() => {
    // Fetch connection status
    axios.get('/api/tiktok/status').then(res => {
      setIsConnected(res.data.is_connected);
      setActiveRoom(res.data.username);
    }).catch(err => console.error(err));

    // Connect WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    const socket = new WebSocket(`${wsProtocol}//${wsHost}/ws/live`);

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'ai_response') {
        setEvents(prev => [payload, ...prev.slice(0, 49)]);
      } else if (payload.type === 'raw_event' && payload.data.type === 'chat') {
        const d = payload.data;
        setEvents(prev => [{ user_name: d.user_name, comment: d.comment, type: 'chat' }, ...prev.slice(0, 49)]);
      }
    };

    return () => {
      socket.close();
    };
  }, []);

  const handleSendManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualComment.trim()) return;
    try {
      await axios.post('/api/manual_chat', {
        user_name: manualUser,
        comment: manualComment
      });
      setManualComment('');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', height: 'calc(100vh - 120px)' }}>
      {/* Live Stream Stream Log & Feed */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: isConnected ? '#10b981' : '#ef4444',
              boxShadow: isConnected ? '0 0 10px #10b981' : 'none'
            }} />
            <h2 style={{ fontSize: '20px', fontWeight: 'bold' }}>
              {isConnected ? `Đang Phát Trực Tiếp: @${activeRoom || 'Simulation'}` : 'Chưa Kết Nối Phòng Live'}
            </h2>
          </div>
          <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>{events.length} Sự kiện</span>
        </div>

        {/* Live Feed List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '4px' }}>
          {events.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
              Chưa có bình luận nào. Hãy kết nối TikTok Live hoặc thử gửi bình luận thủ công bên cạnh.
            </div>
          ) : (
            events.map((item, idx) => (
              <div key={idx} className="glass-card" style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <MessageSquare size={16} color="var(--accent-cyan)" />
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-cyan)' }}>{item.user_name}</span>
                  </div>
                  {item.matched_product && (
                    <span style={{
                      backgroundColor: 'rgba(236, 72, 153, 0.2)',
                      color: 'var(--accent-pink)',
                      padding: '2px 8px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <ShoppingBag size={12} /> {item.matched_product}
                    </span>
                  )}
                </div>

                {item.comment && (
                  <div style={{ color: '#e2e8f0', fontSize: '15px' }}>{item.comment}</div>
                )}

                {item.ai_reply && (
                  <div style={{
                    marginTop: '6px',
                    padding: '10px 14px',
                    backgroundColor: 'rgba(139, 92, 246, 0.15)',
                    borderLeft: '3px solid var(--accent-purple)',
                    borderRadius: '6px',
                    color: '#f3f4f6',
                    fontSize: '14px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--accent-purple)', fontWeight: 'bold', marginBottom: '4px' }}>
                      <Sparkles size={14} /> AI Host Phản Hồi:
                    </div>
                    {item.ai_reply}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Manual Trigger & Live Simulator Box */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Send size={18} color="var(--accent-purple)" /> Giả Lập Bình Luận
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
          Gửi tin nhắn mẫu để kiểm tra ngay lập tức quy trình xử lý của AI, khớp sản phẩm và phát giọng nói TTS.
        </p>

        <form onSubmit={handleSendManual} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>Tên khán giả</label>
            <input
              type="text"
              className="input-field"
              value={manualUser}
              onChange={(e) => setManualUser(e.target.value)}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>Nội dung bình luận</label>
            <textarea
              className="input-field"
              rows={4}
              placeholder="Ví dụ: Áo này giá bao nhiêu shop ơi?"
              value={manualComment}
              onChange={(e) => setManualComment(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary" style={{ justifyContent: 'center', marginTop: '10px' }}>
            <Sparkles size={16} /> Gửi Bình Luận Dùng Thử
          </button>
        </form>

        <div style={{ marginTop: 'auto', padding: '14px', borderRadius: '10px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
            <Volume2 size={16} /> Trạng Thái TTS Queue
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Giọng đọc Edge-TTS Tiếng Việt tự động xếp hàng và phát qua OBS Browser Source.
          </p>
        </div>
      </div>
    </div>
  );
};
