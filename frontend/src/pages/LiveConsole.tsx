import React, { useState, useEffect } from 'react';
import { MessageSquare, Send, Sparkles, Volume2, ShoppingBag } from 'lucide-react';
import axios from 'axios';

interface LiveEvent {
  user_name: string;
  comment?: string;
  ai_reply?: string;
  matched_product?: string;
  type: string;
  user_message?: string;
}

export const LiveConsole: React.FC = () => {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [manualUser, setManualUser] = useState('Khán Giả Demo');
  const [manualComment, setManualComment] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [activeRoom, setActiveRoom] = useState('');
  const [isAudioUnlocked, setIsAudioUnlocked] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);

  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const SILENT_SOUND = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';

  const unlockAudio = () => {
    if (audioRef.current) {
      const prevSrc = audioRef.current.src;
      if (!prevSrc) {
        audioRef.current.src = SILENT_SOUND;
      }
      audioRef.current.play().then(() => {
        setIsAudioUnlocked(true);
        setAudioError(null);
      }).catch((err) => {
        console.warn('Audio play error during unlock:', err);
        setAudioError('Trình duyệt đã chặn autoplay. Hãy bấm nút Bật Âm Thanh Tab bên dưới.');
      });
    }
  };

  useEffect(() => {
    // Setup audio end/error events
    if (audioRef.current) {
      audioRef.current.onended = () => setIsPlayingAudio(false);
      audioRef.current.onerror = () => {
        setIsPlayingAudio(false);
        setAudioError('Không thể tải file âm thanh TTS.');
      };
    }

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
      } else if (payload.type === 'raw_event') {
        const d = payload.data;
        if (d.type === 'chat') {
          setEvents(prev => [{ user_name: d.user_name, comment: d.comment, type: 'chat' }, ...prev.slice(0, 49)]);
        } else if (d.type === 'member') {
          setEvents(prev => [{ user_name: d.user_name, user_message: 'Vừa vào phòng livestream', type: 'member' }, ...prev.slice(0, 49)]);
        }
      } else if (payload.type === 'tts_play' && payload.audio_url) {
        if (audioRef.current) {
          setAudioError(null);
          setIsPlayingAudio(true);
          audioRef.current.src = payload.audio_url;
          audioRef.current.play().then(() => {
            setIsAudioUnlocked(true);
          }).catch(err => {
            console.warn('Audio play blocked:', err);
            setIsAudioUnlocked(false);
            setIsPlayingAudio(false);
            setAudioError('Âm thanh bị trình duyệt chặn! Bấm nút Bật Âm Thanh Tab bên dưới.');
          });
        }
      }
    };

    return () => {
      socket.close();
    };
  }, []);

  const handleSendManual = async (e: React.FormEvent) => {
    e.preventDefault();
    unlockAudio();
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

  const handleSimulateJoin = async () => {
    unlockAudio();
    try {
      await axios.post('/api/manual_event', {
        user_name: manualUser || 'Khách Mới',
        event_type: 'member'
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleTestTTS = async () => {
    unlockAudio();
    try {
      await axios.post('/api/tts/test', {
        text: 'Xin chào! Giọng đọc Edge-TTS AI đang hoạt động bình thường.'
      });
    } catch (err) {
      console.error(err);
      setAudioError('Lỗi kết nối server tạo âm thanh mẫu.');
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', height: 'calc(100vh - 120px)' }}>
      <audio ref={audioRef} />
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

                {(item.comment || item.user_message) && (
                  <div style={{ color: item.user_message ? 'var(--accent-pink)' : '#e2e8f0', fontSize: '15px' }}>
                    {item.comment || item.user_message}
                  </div>
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
          <Send size={18} color="var(--accent-purple)" /> Giả Lập Tương Tác
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
          Gửi tin nhắn hoặc giả lập sự kiện khách vào phòng để kiểm tra quy trình xử lý AI và phát giọng nói TTS.
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
              rows={3}
              placeholder="Ví dụ: Áo này giá bao nhiêu shop ơi?"
              value={manualComment}
              onChange={(e) => setManualComment(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" className="btn-primary" style={{ flex: 1, justifyContent: 'center' }}>
              <Sparkles size={16} /> Gửi Bình Luận
            </button>
            <button type="button" onClick={handleSimulateJoin} className="btn-secondary" style={{ justifyContent: 'center' }}>
              👋 Khách Vào Phòng
            </button>
          </div>
        </form>

        <div style={{ marginTop: 'auto', padding: '14px', borderRadius: '10px', backgroundColor: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
              <Volume2 size={16} className={isPlayingAudio ? 'pulse' : ''} /> 
              Trạng Thái Giọng Nói TTS
              {isPlayingAudio && <span style={{ color: '#10b981', fontSize: '11px', fontStyle: 'italic' }}>(Đang phát...)</span>}
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                type="button"
                onClick={handleTestTTS}
                style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--accent-purple)', background: 'rgba(139, 92, 246, 0.15)', color: 'var(--accent-purple)', cursor: 'pointer' }}
              >
                🔊 Thử Phát Âm Thanh
              </button>
              <button
                type="button"
                onClick={() => {
                  unlockAudio();
                }}
                style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--accent-cyan)', background: isAudioUnlocked ? 'rgba(16, 185, 129, 0.2)' : 'transparent', color: isAudioUnlocked ? '#10b981' : 'var(--accent-cyan)', cursor: 'pointer' }}
              >
                {isAudioUnlocked ? '🔊 Âm Thanh Đã Bật' : '🔊 Bật Âm Thanh Tab'}
              </button>
            </div>
          </div>

          {audioError && (
            <div style={{ fontSize: '12px', color: '#f87171', backgroundColor: 'rgba(239, 68, 68, 0.1)', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              ⚠️ {audioError}
            </div>
          )}

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Giọng đọc Edge-TTS Tiếng Việt phát trực tiếp trên tab và đồng bộ qua OBS Overlay source (<a href="http://localhost:8000/static/scene/index.html" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-purple)' }}>/static/scene/index.html</a>).
          </p>
        </div>
      </div>
    </div>
  );
};
