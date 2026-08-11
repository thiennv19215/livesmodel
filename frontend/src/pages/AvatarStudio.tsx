import React, { useState, useEffect } from 'react';
import { Camera, ExternalLink, Copy, Check, Save, RefreshCw } from 'lucide-react';
import { CapCutCanvas } from '../components/CapCutCanvas';
import type { SceneConfig, SceneElement } from '../components/CapCutCanvas';
import { CapCutInspector } from '../components/CapCutInspector';
import { CapCutTimeline } from '../components/CapCutTimeline';
import { CapCutSourcesPanel } from '../components/CapCutSourcesPanel';

export const AvatarStudio: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [selectedElement, setSelectedElement] = useState<SceneElement | null>('avatar');
  const [isPlayingTest, setIsPlayingTest] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [avatarUploadError, setAvatarUploadError] = useState<string | null>(null);
  const [avatarUploadSuccess, setAvatarUploadSuccess] = useState(false);
  const [isUploadingVideo, setIsUploadingVideo] = useState(false);
  const [videoUploadError, setVideoUploadError] = useState<string | null>(null);
  const [videoUploadSuccess, setVideoUploadSuccess] = useState(false);

  const [config, setConfig] = useState<SceneConfig>({
    aspect_ratio: '9:16',
    video_media_url: '',
    video_name: '',
    video_x: 50,
    video_y: 50,
    video_width: 100,
    video_height: 100,
    video_rotation: 0,
    video_fit: 'contain',
    video_visible: true,
    avatar_x: 50,
    avatar_y: 65,
    avatar_scale: 100,
    avatar_style: 'default',
    avatar_mode: 'builtin',
    avatar_media_url: '',
    avatar_fit: 'contain',
    avatar_visible: true,
    caption_x: 50,
    caption_y: 88,
    caption_font_size: 18,
    caption_text_color: '#ffffff',
    caption_bg_color: 'rgba(15, 23, 42, 0.85)',
    caption_preset: 'capcut_yellow',
    caption_visible: true,
    bg_mode: 'transparent',
  });

  const sceneUrl = `${window.location.protocol}//${window.location.host}/static/scene/index.html`;

  useEffect(() => {
    fetch('/api/settings/scene')
      .then((res) => res.json())
      .then((data) => {
        if (data) setConfig((prev) => ({ ...prev, ...data }));
      })
      .catch((err) => console.log('Loaded default studio config', err));
  }, []);

  const handleConfigChange = (newPartial: Partial<SceneConfig>) => {
    setConfig((prev) => {
      const updated = { ...prev, ...newPartial };
      // Auto save or push updates
      return updated;
    });
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/settings/scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        throw new Error(`Không thể lưu cấu hình (${response.status})`);
      }
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      console.error('Save error:', err);
    } finally {
      setSaving(false);
    }
  };

  const uploadAvatarVideo = async (file: File) => {
    setIsUploadingAvatar(true);
    setAvatarUploadError(null);
    setAvatarUploadSuccess(false);
    try {
      const formData = new FormData();
      formData.append('video', file);
      const response = await fetch('/api/avatar/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Không thể tải video (${response.status})`);
      }
      handleConfigChange({
        avatar_mode: 'video',
        avatar_media_url: data.media_url,
      });
      setSelectedElement('avatar');
      setAvatarUploadSuccess(true);
    } catch (err) {
      setAvatarUploadError(err instanceof Error ? err.message : 'Không thể tải video');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const uploadSourceVideo = async (file: File) => {
    setIsUploadingVideo(true);
    setVideoUploadError(null);
    setVideoUploadSuccess(false);
    try {
      const formData = new FormData();
      formData.append('video', file);
      const response = await fetch('/api/media/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Không thể tải video nguồn (${response.status})`);
      }
      handleConfigChange({
        video_media_url: data.media_url,
        video_name: file.name,
        video_visible: true,
        video_x: 50,
        video_y: 50,
        video_width: 100,
        video_height: 100,
        video_rotation: 0,
      });
      setSelectedElement('video');
      setVideoUploadSuccess(true);
    } catch (err) {
      setVideoUploadError(err instanceof Error ? err.message : 'Không thể tải video nguồn');
    } finally {
      setIsUploadingVideo(false);
    }
  };

  const removeSourceVideo = () => {
    handleConfigChange({
      video_media_url: '',
      video_name: '',
      video_visible: true,
      video_x: 50,
      video_y: 50,
      video_width: 100,
      video_height: 100,
      video_rotation: 0,
    });
    setVideoUploadError(null);
    setVideoUploadSuccess(false);
    setSelectedElement('avatar');
  };

  const copyUrl = () => {
    navigator.clipboard.writeText(sceneUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTestSpeech = async () => {
    setIsPlayingTest(true);
    try {
      const response = await fetch('/api/tts/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: 'Xin chào! Đây là MC AI livestream thử nghiệm giọng đọc CapCut Studio!' }),
      });
      if (!response.ok) {
        throw new Error(`Không thể tạo giọng đọc thử (${response.status})`);
      }
    } catch (err) {
      console.error('Test speech error', err);
    }
    setTimeout(() => setIsPlayingTest(false), 4000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: 'calc(100vh - 100px)' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Camera size={24} color="var(--accent-purple)" /> CapCut Avatar Studio & OBS Scene Editor
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '4px' }}>
            Kéo thả, căn chỉnh vị trí MC ảo AI và Phụ đề theo phong cách CapCut chuyên nghiệp.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={saveConfig} className="btn-primary" disabled={saving}>
            {saving ? <RefreshCw size={16} className="animate-spin" /> : savedSuccess ? <Check size={16} /> : <Save size={16} />}
            {saving ? 'Đang lưu...' : savedSuccess ? 'Đã Lưu & Cập Nhật OBS' : 'Lưu Vị Trí & Cấu Hình'}
          </button>
        </div>
      </div>

      {/* OBS URL Link Banner */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'rgba(15, 23, 42, 0.85)', padding: '12px 20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 600 }}>OBS Browser Source URL:</span>
          <code style={{ color: 'var(--accent-cyan)', fontWeight: 'bold', fontSize: '13px' }}>{sceneUrl}</code>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={copyUrl} className="btn-secondary" style={{ padding: '6px 14px', fontSize: '12px' }}>
            {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? 'Đã Copy' : 'Copy URL'}
          </button>
          <a href={sceneUrl} target="_blank" rel="noreferrer" className="btn-secondary" style={{ padding: '6px 14px', fontSize: '12px' }}>
            <ExternalLink size={14} /> Xem Trực Tiếp
          </a>
        </div>
      </div>

      {/* Main CapCut Editor Layout: Canvas + Inspector */}
      <div className="capcut-editor-layout" style={{ height: '620px', display: 'flex', gap: '16px', minHeight: 0, overflowX: 'auto' }}>
        <CapCutSourcesPanel
          config={config}
          selectedElement={selectedElement}
          onSelectElement={setSelectedElement}
          onChangeConfig={handleConfigChange}
          onUploadVideo={uploadSourceVideo}
          onRemoveVideo={removeSourceVideo}
          isUploadingVideo={isUploadingVideo}
          videoUploadError={videoUploadError}
          videoUploadSuccess={videoUploadSuccess}
        />

        {/* Left Interactive Canvas Editor */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: '320px' }}>
          <CapCutCanvas
            config={config}
            onChangeConfig={handleConfigChange}
            selectedElement={selectedElement}
            onSelectElement={setSelectedElement}
            isSpeakingTest={isPlayingTest}
          />
        </div>

        {/* Right CapCut Property Inspector Panel */}
        <CapCutInspector
          config={config}
          onChangeConfig={handleConfigChange}
          selectedElement={selectedElement}
          onSelectElement={(el) => setSelectedElement(el)}
          onTestSpeech={handleTestSpeech}
          onUploadAvatar={uploadAvatarVideo}
          isUploadingAvatar={isUploadingAvatar}
          avatarUploadError={avatarUploadError}
          avatarUploadSuccess={avatarUploadSuccess}
        />
      </div>

      {/* Bottom CapCut Multi-Track Timeline Panel */}
      <CapCutTimeline
        selectedElement={selectedElement}
        onSelectElement={(el) => setSelectedElement(el)}
        isPlaying={isPlayingTest}
        onPlayTest={handleTestSpeech}
        hasVideo={Boolean(config.video_media_url)}
      />
    </div>
  );
};
