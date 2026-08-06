import React from 'react';
import { Camera, ExternalLink, Copy, Check } from 'lucide-react';

export const AvatarStudio: React.FC = () => {
  const [copied, setCopied] = React.useState(false);
  const sceneUrl = `${window.location.protocol}//${window.location.host}/static/scene/index.html`;

  const copyUrl = () => {
    navigator.clipboard.writeText(sceneUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Camera size={24} color="var(--accent-purple)" /> Avatar Studio & OBS Overlay Browser Source
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
            Đưa hình ảnh MC ảo AI và Phụ đề vào phần mềm OBS Studio để phát trực tiếp lên TikTok / Facebook / YouTube.
          </p>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'rgba(15, 23, 42, 0.8)', padding: '14px 20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>OBS Browser Source URL:</span>
            <code style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>{sceneUrl}</code>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={copyUrl} className="btn-secondary">
              {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? 'Đã Coppy' : 'Coppy URL'}
            </button>
            <a href={sceneUrl} target="_blank" rel="noreferrer" className="btn-primary">
              <ExternalLink size={16} /> Mở Xem Trực Tiếp
            </a>
          </div>
        </div>

        {/* Live Preview Iframe */}
        <div style={{
          width: '100%',
          height: '500px',
          borderRadius: '16px',
          overflow: 'hidden',
          border: '2px solid rgba(139, 92, 246, 0.3)',
          backgroundColor: '#000',
          position: 'relative'
        }}>
          <iframe
            src={sceneUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="OBS Scene Preview"
          />
        </div>
      </div>
    </div>
  );
};
