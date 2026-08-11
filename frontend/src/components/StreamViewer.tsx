import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Link2, LoaderCircle, Play, Radio, RotateCcw, Trash2 } from 'lucide-react';

export interface StreamStatus {
  is_configured: boolean;
  label: string;
  source_type: 'hls' | 'video' | 'auto' | '';
  source_url: string;
  playback_url: string;
  updated_at?: number | null;
  last_error?: string;
}

interface StreamViewerProps {
  status: StreamStatus | null;
  onStatusChange: (status: StreamStatus) => void;
}

const emptyStatus: StreamStatus = {
  is_configured: false,
  label: '',
  source_type: '',
  source_url: '',
  playback_url: '',
};

export const StreamViewer: React.FC<StreamViewerProps> = ({ status, onStatusChange }) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [sourceUrl, setSourceUrl] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [playerKey, setPlayerKey] = useState(0);
  const [playerState, setPlayerState] = useState<'idle' | 'loading' | 'playing' | 'error'>('idle');
  const [error, setError] = useState('');
  const currentStatus = status ?? emptyStatus;

  useEffect(() => {
    if (status?.source_url) setSourceUrl(status.source_url);
  }, [status?.source_url]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !currentStatus.playback_url) {
      setPlayerState('idle');
      return;
    }

    setPlayerState('loading');
    setError('');
    let disposed = false;
    let hls: import('hls.js').default | null = null;

    const markPlaying = () => setPlayerState('playing');
    const markError = () => {
      setPlayerState('error');
      setError('Không phát được nguồn này. Hãy kiểm tra URL HLS/MP4 và thử tải lại.');
    };
    video.addEventListener('playing', markPlaying);
    video.addEventListener('error', markError);

    if (currentStatus.source_type !== 'video') {
      void import('hls.js').then(({ default: Hls }) => {
        if (disposed) return;
        if (!Hls.isSupported()) {
          video.src = currentStatus.playback_url;
          void video.play().catch(() => undefined);
          return;
        }
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 30,
        });
        hls.loadSource(currentStatus.playback_url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          void video.play().catch(() => undefined);
        });
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (!data.fatal) return;
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            hls?.startLoad();
          } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            hls?.recoverMediaError();
          } else {
            markError();
            hls?.destroy();
            hls = null;
          }
        });
      }).catch(markError);
    } else {
      video.src = currentStatus.playback_url;
      void video.play().catch(() => undefined);
    }

    return () => {
      disposed = true;
      video.removeEventListener('playing', markPlaying);
      video.removeEventListener('error', markError);
      hls?.destroy();
      video.removeAttribute('src');
      video.load();
    };
  }, [currentStatus.playback_url, currentStatus.source_type, playerKey]);

  const saveSource = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!sourceUrl.trim()) return;
    setIsSaving(true);
    setError('');
    try {
      const response = await axios.put<StreamStatus>('/api/stream/source', {
        url: sourceUrl.trim(),
        label: 'Luồng trực tiếp',
      });
      onStatusChange(response.data);
      setPlayerKey((value) => value + 1);
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.detail || 'Backend không nhận được nguồn phát.');
      } else {
        setError('Không thể lưu nguồn phát.');
      }
      setPlayerState('error');
    } finally {
      setIsSaving(false);
    }
  };

  const clearSource = async () => {
    try {
      const response = await axios.delete<StreamStatus>('/api/stream/source');
      onStatusChange(response.data);
      setSourceUrl('');
      setError('');
    } catch {
      setError('Không thể xóa nguồn phát.');
    }
  };

  const statusColor = playerState === 'playing' ? '#10b981' : playerState === 'error' ? '#ef4444' : '#f59e0b';
  const statusLabel = playerState === 'playing' ? 'Đang phát' : playerState === 'loading' ? 'Đang tải' : playerState === 'error' ? 'Lỗi phát' : 'Chưa có nguồn';

  return (
    <section className="glass-card stream-viewer" style={{ padding: '14px', display: 'grid', gridTemplateColumns: 'minmax(280px, 1.3fr) minmax(240px, 0.7fr)', gap: '14px' }}>
      <div style={{ position: 'relative', minHeight: '210px', aspectRatio: '16 / 9', borderRadius: '10px', overflow: 'hidden', background: '#05070c', border: '1px solid var(--border-color)' }}>
        <video
          key={playerKey}
          ref={videoRef}
          controls
          playsInline
          muted
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: currentStatus.is_configured ? 'block' : 'none' }}
        />
        {!currentStatus.is_configured && (
          <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>
            <div>
              <Radio size={30} style={{ marginBottom: '8px' }} />
              <div>Nhập URL HLS (.m3u8) hoặc video MP4 để xem luồng.</div>
            </div>
          </div>
        )}
        <div style={{ position: 'absolute', top: '10px', left: '10px', display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '5px 9px', borderRadius: '999px', background: 'rgba(5, 7, 12, 0.78)', fontSize: '12px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: statusColor }} />
          {statusLabel}
        </div>
      </div>

      <form onSubmit={saveSource} style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}>
          <Play size={17} color="var(--accent-cyan)" /> Xem luồng qua backend
        </div>
        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.5 }}>
          Backend kiểm tra URL, giữ nguồn phát và chuyển tiếp playlist/segment để trình duyệt phát ổn định.
        </p>
        <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }} htmlFor="stream-source-url">URL nguồn phát</label>
        <div style={{ position: 'relative' }}>
          <Link2 size={15} style={{ position: 'absolute', left: '11px', top: '12px', color: 'var(--text-secondary)' }} />
          <input
            id="stream-source-url"
            className="input-field"
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            placeholder="https://cdn.example.com/live/index.m3u8"
            style={{ paddingLeft: '34px' }}
          />
        </div>
        {error && <div style={{ color: '#f87171', fontSize: '12px', lineHeight: 1.4 }}>{error}</div>}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: 'auto' }}>
          <button type="submit" className="btn-primary" disabled={isSaving || !sourceUrl.trim()} style={{ padding: '8px 12px' }}>
            {isSaving ? <LoaderCircle size={15} className="animate-spin" /> : <Play size={15} />}
            Mở luồng
          </button>
          {currentStatus.is_configured && (
            <>
              <button type="button" className="btn-secondary" onClick={() => setPlayerKey((value) => value + 1)} style={{ padding: '8px 12px' }}>
                <RotateCcw size={15} /> Tải lại
              </button>
              <button type="button" className="btn-secondary" onClick={clearSource} style={{ padding: '8px 12px' }}>
                <Trash2 size={15} /> Xóa
              </button>
            </>
          )}
        </div>
      </form>
    </section>
  );
};
