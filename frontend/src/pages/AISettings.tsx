import React, { useState, useEffect } from 'react';
import { Cpu, Save, Check } from 'lucide-react';
import axios from 'axios';

export const AISettings: React.FC = () => {
  const [form, setForm] = useState({
    provider: 'openai',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
    system_prompt: ''
  });
  const [saved, setSaved] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);

  const changeProvider = (provider: string) => {
    const defaults: Record<string, { base_url: string; model: string }> = {
      openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
      openrouter: { base_url: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o-mini' },
      ollama: { base_url: 'http://localhost:11434', model: 'llama3' },
    };
    setForm(current => ({ ...current, provider, ...defaults[provider] }));
  };

  useEffect(() => {
    axios.get('/api/settings/ai').then(res => {
      setHasApiKey(Boolean(res.data.has_api_key));
      setForm({
        provider: res.data.provider,
        api_key: '',
        base_url: res.data.base_url,
        model: res.data.model,
        system_prompt: res.data.system_prompt,
      });
    }).catch(err => console.error(err));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/api/settings/ai', form);
      if (form.api_key.trim()) {
        setHasApiKey(true);
        setForm(current => ({ ...current, api_key: '' }));
      }
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
          <Cpu size={24} color="var(--accent-purple)" /> Cấu Hình AI Model (LLM Provider)
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
          Thiết lập nhà cung cấp AI để đóng vai MC livestream trả lời tự động câu hỏi của khán giả.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>AI Provider</label>
            <select
              className="input-field"
              value={form.provider}
              onChange={e => changeProvider(e.target.value)}
            >
              <option value="openai">OpenAI (GPT-4o-mini / GPT-4o)</option>
              <option value="ollama">Ollama (Chạy local máy tính)</option>
              <option value="openrouter">OpenRouter / DeepSeek</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>API Key</label>
            <input
              type="password"
              className="input-field"
              placeholder="sk-..."
              value={form.api_key}
              onChange={e => setForm({ ...form, api_key: e.target.value })}
            />
            {hasApiKey && !form.api_key && (
              <small style={{ display: 'block', marginTop: '6px', color: 'var(--text-secondary)' }}>
                API key đã được cấu hình. Để trống để giữ nguyên khóa hiện tại.
              </small>
            )}
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>API Base URL</label>
            <input
              type="text"
              className="input-field"
              value={form.base_url}
              onChange={e => setForm({ ...form, base_url: e.target.value })}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Tên Model AI</label>
            <input
              type="text"
              className="input-field"
              value={form.model}
              onChange={e => setForm({ ...form, model: e.target.value })}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>System Prompt (Tính cách MC)</label>
            <textarea
              className="input-field"
              rows={4}
              value={form.system_prompt}
              onChange={e => setForm({ ...form, system_prompt: e.target.value })}
            />
          </div>

          <button type="submit" className="btn-primary" style={{ width: 'fit-content' }}>
            {saved ? <Check size={16} /> : <Save size={16} />} {saved ? 'Đã Lưu Cấu Hình' : 'Lưu Thay Đổi'}
          </button>
        </form>
      </div>
    </div>
  );
};
