import React, { useState, useEffect } from 'react';
import { Volume2, Save, Check } from 'lucide-react';
import axios from 'axios';

export const TTSSettings: React.FC = () => {
  const [form, setForm] = useState({
    voice: 'vi-VN-HoaiMyNeural',
    rate: '+0%',
    pitch: '+0Hz'
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    axios.get('/api/settings/tts').then(res => setForm(res.data)).catch(err => console.error(err));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/api/settings/tts', form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-panel" style={{ padding: '32px' }}>
        <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <Volume2 size={24} color="var(--accent-purple)" /> Cấu Hình Giọng Đọc AI (Edge-TTS)
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
          Tự động chuyển câu trả lời văn bản của AI thành giọng phát trực tiếp truyền cảm trên livestream.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Giọng Đọc Tiếng Việt</label>
            <select className="input-field" value={form.voice} onChange={e => setForm({ ...form, voice: e.target.value })}>
              <option value="vi-VN-HoaiMyNeural">Hoài My (Nữ - Truyền cảm, miền Nam)</option>
              <option value="vi-VN-NamMinhNeural">Nam Minh (Nam - Chân thật, miền Bắc)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Tốc Độ Đọc (Rate)</label>
            <input type="text" className="input-field" value={form.rate} onChange={e => setForm({ ...form, rate: e.target.value })} placeholder="+0%" />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Tone Giọng (Pitch)</label>
            <input type="text" className="input-field" value={form.pitch} onChange={e => setForm({ ...form, pitch: e.target.value })} placeholder="+0Hz" />
          </div>

          <button type="submit" className="btn-primary" style={{ width: 'fit-content' }}>
            {saved ? <Check size={16} /> : <Save size={16} />} {saved ? 'Đã Lưu Cấu Hình' : 'Lưu Thay Đổi'}
          </button>
        </form>
      </div>
    </div>
  );
};
