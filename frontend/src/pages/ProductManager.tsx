import React, { useState, useEffect } from 'react';
import { Package, Plus, Trash2, Tag } from 'lucide-react';
import axios from 'axios';

interface Product {
  id: number;
  name: string;
  keywords: string;
  price: string;
  selling_points: string;
  custom_script: string;
}

export const ProductManager: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    name: '',
    keywords: '',
    price: '',
    selling_points: '',
    custom_script: ''
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const res = await axios.get('/api/products');
      setProducts(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/api/products', form);
      setShowModal(false);
      setForm({ name: '', keywords: '', price: '', selling_points: '', custom_script: '' });
      fetchProducts();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Bạn có chắc chắn muốn xóa sản phẩm này?')) return;
    try {
      await axios.delete(`/api/products/${id}`);
      fetchProducts();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Package size={24} color="var(--accent-purple)" /> Danh Mục Sản Phẩm & Kịch Bản Cho AI
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
            Khai báo các sản phẩm bán trong buổi livestream để AI tự động khớp câu hỏi khán giả và tư vấn chốt đơn.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={18} /> Thêm Sản Phẩm Mới
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
        {products.length === 0 ? (
          <div className="glass-panel" style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Chưa có sản phẩm nào. Nhấn "Thêm Sản Phẩm Mới" để bắt đầu thiết lập kịch bản bán hàng.
          </div>
        ) : (
          products.map(prod => (
            <div key={prod.id} className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', position: 'relative' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: 'white' }}>{prod.name}</h3>
                <button onClick={() => handleDelete(prod.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}>
                  <Trash2 size={18} />
                </button>
              </div>

              {prod.price && (
                <div style={{ color: 'var(--accent-pink)', fontWeight: 'bold', fontSize: '15px' }}>
                  💰 Giá: {prod.price}
                </div>
              )}

              {prod.keywords && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  <Tag size={14} color="var(--accent-cyan)" />Từ khóa khớp: <span style={{ color: '#e2e8f0' }}>{prod.keywords}</span>
                </div>
              )}

              {prod.selling_points && (
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', backgroundColor: 'rgba(15,23,42,0.5)', padding: '10px', borderRadius: '8px' }}>
                  <strong>Điểm nổi bật:</strong> {prod.selling_points}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="glass-panel" style={{ width: '500px', padding: '28px', backgroundColor: '#1e293b' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>Thêm Sản Phẩm Mới</h3>
            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Tên sản phẩm</label>
                <input className="input-field" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Áo Thun Unisex Premium" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Giá sản phẩm</label>
                <input className="input-field" value={form.price} onChange={e => setForm({ ...form, price: e.target.value })} placeholder="199.000đ" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Từ khóa nhận diện (Phân cách bằng dấu phẩy)</label>
                <input className="input-field" value={form.keywords} onChange={e => setForm({ ...form, keywords: e.target.value })} placeholder="áo thun, size L, màu đen, chất liệu" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Điểm nổi bật / Ưu đãi</label>
                <textarea className="input-field" rows={3} value={form.selling_points} onChange={e => setForm({ ...form, selling_points: e.target.value })} placeholder="Cotton 100% thoáng mát, mua 2 tặng 1 khẩu trang" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Kịch bản tư vấn ưu tiên cho AI</label>
                <textarea className="input-field" rows={3} value={form.custom_script} onChange={e => setForm({ ...form, custom_script: e.target.value })} placeholder="Nhấn mạnh chất liệu, hỏi size khách cần và mời chốt đơn tự nhiên" />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Hủy</button>
                <button type="submit" className="btn-primary">Lưu Sản Phẩm</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
