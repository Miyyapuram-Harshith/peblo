import { useState, useEffect, createContext, useContext, useRef } from 'react';
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { api } from './api';

// --- Auth Context ---
interface AuthState { user: { id: string; email: string; role: string } | null; loading: boolean; }
const AuthContext = createContext<AuthState & { login: (e: string, p: string) => Promise<void>; logout: () => void }>({
  user: null, loading: true, login: async () => {}, logout: () => {},
});

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthState['user']>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (api.getToken()) {
      api.getMe().then(setUser).catch(() => { api.logout(); }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    await api.login(email, password);
    const me = await api.getMe();
    setUser(me);
  };

  const logout = () => { api.logout(); setUser(null); };

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

function useAuth() { return useContext(AuthContext); }

// --- Icons (inline SVG) ---
const Icons = {
  dashboard: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  shows: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/></svg>,
  episodes: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  publish: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>,
  check: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  x: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  alert: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  search: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  menu: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>,
  lock: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>,
  upload: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
  trash: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>,
  logout: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
};

// --- Login Page ---
function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      toast.success('Welcome to Peblo Studio');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>🎬 Peblo Studio</h1>
        <p className="subtitle">Content Operations & Publishing</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Email</label>
            <input id="email" className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@peblo.local" required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input id="password" className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
          </div>
          {error && <div className="form-error mb-4">{error}</div>}
          <button className="btn btn-primary btn-lg" style={{ width: '100%' }} type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Sign In'}
          </button>
        </form>
        <div style={{ marginTop: 24, padding: 16, background: '#f8fafc', borderRadius: 8, fontSize: '0.8rem', color: '#64748b' }}>
          <strong>Demo Credentials</strong><br />
          Admin: admin@peblo.local / admin123<br />
          Editor: editor@peblo.local / editor123
        </div>
      </div>
    </div>
  );
}

// --- Dashboard ---
function Dashboard() {
  // Removed unused user variable
  const { data: showsData } = useQuery({ queryKey: ['shows', { page: 1, page_size: 1 }], queryFn: () => api.listShows({ page: 1, page_size: 1 }) });
  const { data: episodesData } = useQuery({ queryKey: ['episodes-count'], queryFn: () => api.listEpisodes({ page: 1, page_size: 1 }) });
  const { data: publishedEps } = useQuery({ queryKey: ['episodes-published-count'], queryFn: () => api.listEpisodes({ page: 1, page_size: 1, status: 'published' }) });
  const { data: validation } = useQuery({ queryKey: ['validation'], queryFn: () => api.getValidationReport() });
  const { data: publishRuns } = useQuery({ queryKey: ['publish-runs'], queryFn: () => api.listPublishRuns(5) });

  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening';
  const latestRun = publishRuns?.items?.[0];

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Content Operations</h2>
          <p>{greeting} 👋</p>
        </div>
      </div>
      <div className="page-body">
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon purple">{Icons.shows}</div>
            <div className="stat-content">
              <div className="stat-label">Shows</div>
              <div className="stat-value">{showsData?.total ?? <span className="skeleton" style={{width:40,height:28,display:'inline-block'}} />}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon blue">{Icons.episodes}</div>
            <div className="stat-content">
              <div className="stat-label">Episodes</div>
              <div className="stat-value">{episodesData?.total ?? <span className="skeleton" style={{width:40,height:28,display:'inline-block'}} />}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green">{Icons.check}</div>
            <div className="stat-content">
              <div className="stat-label">Published Episodes</div>
              <div className="stat-value">{publishedEps?.total ?? <span className="skeleton" style={{width:40,height:28,display:'inline-block'}} />}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{background: validation?.blocking_count ? '#fee2e2' : '#dcfce7', color: validation?.blocking_count ? '#dc2626' : '#16a34a'}}>{Icons.alert}</div>
            <div className="stat-content">
              <div className="stat-label">Blocking Issues</div>
              <div className="stat-value">{validation?.blocking_count ?? <span className="skeleton" style={{width:40,height:28,display:'inline-block'}} />}</div>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <h3>Catalogue Health</h3>
              {validation && (
                <div className={`health-badge ${validation.ready ? 'ready' : 'blocked'}`}>
                  <span className={`health-dot ${validation.ready ? 'ready' : 'blocked'}`} />
                  {validation.ready ? 'Ready to Publish' : 'Blocked'}
                </div>
              )}
            </div>
            <div className="card-body">
              {validation ? (
                validation.ready ? (
                  <p style={{ color: '#16a34a', fontWeight: 500 }}>✅ All content passes validation. Ready to publish.</p>
                ) : (
                  <div>
                    <p style={{ marginBottom: 12 }}>{validation.blocking_count} issue{validation.blocking_count !== 1 ? 's' : ''} blocking publication</p>
                    {validation.issues.filter(i => i.severity === 'blocking').slice(0, 3).map((issue, idx) => (
                      <div key={idx} className="issue-item blocking" style={{ marginBottom: 8 }}>
                        <div className="issue-content">
                          <div className="issue-title">{issue.message}</div>
                          <div className="issue-action">{issue.suggested_action}</div>
                        </div>
                      </div>
                    ))}
                    <Link to="/validation" className="btn btn-secondary btn-sm mt-4">Review All Issues</Link>
                  </div>
                )
              ) : (
                <div className="skeleton" style={{height:60}} />
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Latest Publish</h3>
            </div>
            <div className="card-body">
              {latestRun ? (
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <span className={`badge badge-${latestRun.status === 'success' ? 'success' : 'error'}`}>{latestRun.status}</span>
                    <span className="text-sm text-muted">v{latestRun.shows_count || 0} shows</span>
                  </div>
                  <div style={{fontSize:'0.8rem',color:'#64748b'}}>
                    <p>Shows: {latestRun.shows_count || 0}</p>
                    <p>Episodes: {latestRun.episodes_count || 0}</p>
                    <p>Languages: {latestRun.language_group_count || 0}</p>
                    {latestRun.catalogue_hash && <p className="font-mono" style={{fontSize:'0.7rem',marginTop:8}}>SHA: {latestRun.catalogue_hash.substring(0, 16)}...</p>}
                  </div>
                </div>
              ) : (
                <div className="empty-state" style={{padding:20}}>
                  <p>No publications yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// --- Shows Page ---
function ShowsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [editingShow, setEditingShow] = useState<any>(null);
  const [showModal, setShowModal] = useState(false);
  const searchTimeout = useRef<number | undefined>(undefined);
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const queryClient = useQueryClient();
  // Removed unused navigate

  useEffect(() => {
    clearTimeout(searchTimeout.current);
    searchTimeout.current = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(searchTimeout.current);
  }, [search]);

  const { data, isLoading } = useQuery({
    queryKey: ['shows', { page, search: debouncedSearch, section: sectionFilter, status: statusFilter }],
    queryFn: () => api.listShows({ page, page_size: 20, search: debouncedSearch || undefined, section: sectionFilter || undefined, status: statusFilter || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteShow(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['shows'] }); toast.success('Show deleted'); },
    onError: (err: any) => toast.error(err.message || 'Delete failed'),
  });

  const totalPages = Math.ceil((data?.total || 0) / 20);

  return (
    <>
      <div className="page-header">
        <div><h2>Shows</h2><p>{data?.total || 0} shows</p></div>
        <button className="btn btn-primary" onClick={() => { setEditingShow(null); setShowModal(true); }}>+ New Show</button>
      </div>
      <div className="page-body">
        <div className="card">
          <div className="toolbar">
            <div className="search-input">
              {Icons.search}
              <input placeholder="Search shows..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
            </div>
            <select className="filter-select" value={sectionFilter} onChange={e => { setSectionFilter(e.target.value); setPage(1); }}>
              <option value="">All Sections</option>
              <option value="Featured">Featured</option>
              <option value="Adventure">Adventure</option>
              <option value="Learning">Learning</option>
              <option value="Stories">Stories</option>
            </select>
            <select className="filter-select" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All Status</option>
              <option value="published">Published</option>
              <option value="draft">Draft</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th>Title</th><th>Section</th><th>Category</th><th>Status</th><th>Artwork</th><th></th></tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}><td colSpan={6}><div className="skeleton" style={{height:20}} /></td></tr>
                  ))
                ) : data?.items?.length ? (
                  data.items.map((show: any) => (
                    <tr key={show.id}>
                      <td><Link to={`/shows/${show.id}`} style={{color:'var(--purple-600)',fontWeight:500,textDecoration:'none'}}>{show.title}</Link></td>
                      <td>{show.section || '—'}</td>
                      <td>{show.category || '—'}</td>
                      <td><span className={`badge badge-${show.status}`}>{show.status}</span></td>
                      <td>{show.artwork?.length || 0} / 2</td>
                      <td>
                        <div className="flex gap-2">
                          <button className="btn btn-ghost btn-sm" onClick={() => { setEditingShow(show); setShowModal(true); }}>Edit</button>
                          <button className="btn btn-ghost btn-sm" style={{color:'var(--red-500)'}} onClick={() => { if(confirm(`Delete "${show.title}"?`)) deleteMutation.mutate(show.id); }}>{Icons.trash}</button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={6}><div className="empty-state"><h3>No shows found</h3><p>Try adjusting your search or filters.</p></div></td></tr>
                )}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="pagination">
              <span className="pagination-info">Page {page} of {totalPages} ({data?.total} total)</span>
              <div className="pagination-controls">
                <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
                <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
              </div>
            </div>
          )}
        </div>
      </div>
      {showModal && <ShowModal show={editingShow} onClose={() => setShowModal(false)} />}
    </>
  );
}

// --- Show Modal ---
function ShowModal({ show, onClose }: { show: any; onClose: () => void }) {
  const [title, setTitle] = useState(show?.title || '');
  const [synopsis, setSynopsis] = useState(show?.synopsis || '');
  const [section, setSection] = useState(show?.section || '');
  const [category, setCategory] = useState(show?.category || '');
  const [status, setStatus] = useState(show?.status || 'draft');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: any) => show ? api.updateShow(show.id, data) : api.createShow(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shows'] });
      toast.success(show ? 'Show updated' : 'Show created');
      onClose();
    },
    onError: (err: any) => toast.error(err.message || 'Failed'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({ title, synopsis, section: section || undefined, category: category || undefined, status });
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>{show ? 'Edit Show' : 'New Show'}</h3>
          <button className="btn btn-ghost" onClick={onClose}>{Icons.x}</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label" htmlFor="show-title">Title <span className="required">*</span></label>
              <input id="show-title" className="form-input" value={title} onChange={e => setTitle(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="show-synopsis">Synopsis</label>
              <textarea id="show-synopsis" className="form-textarea" value={synopsis} onChange={e => setSynopsis(e.target.value)} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label className="form-label" htmlFor="show-section">Section</label>
                <select id="show-section" className="form-select" value={section} onChange={e => setSection(e.target.value)}>
                  <option value="">Select...</option>
                  <option value="Featured">Featured</option>
                  <option value="Adventure">Adventure</option>
                  <option value="Learning">Learning</option>
                  <option value="Stories">Stories</option>
                </select>
                <p className="form-hint">Required for published shows</p>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="show-category">Category</label>
                <select id="show-category" className="form-select" value={category} onChange={e => setCategory(e.target.value)}>
                  <option value="">Select...</option>
                  <option value="Animation">Animation</option>
                  <option value="Educational">Educational</option>
                  <option value="Adventure">Adventure</option>
                  <option value="Comedy">Comedy</option>
                  <option value="Drama">Drama</option>
                  <option value="Musical">Musical</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="show-status">Status</label>
              <select id="show-status" className="form-select" value={status} onChange={e => setStatus(e.target.value)}>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? <span className="spinner" /> : show ? 'Save Changes' : 'Create Show'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --- Show Detail ---
function ShowDetailPage() {
  const location = useLocation();
  const showId = location.pathname.split('/shows/')[1];
  // Removed unused queryClient
  const { data: show, isLoading } = useQuery({ queryKey: ['show', showId], queryFn: () => api.getShow(showId) });
  const { data: seasons } = useQuery({ queryKey: ['seasons', showId], queryFn: () => api.listSeasons(showId), enabled: !!showId });
  const { data: episodes } = useQuery({ queryKey: ['episodes', { show_id: showId }], queryFn: () => api.listEpisodes({ show_id: showId, page_size: 100 }), enabled: !!showId });

  if (isLoading) return <div className="page-body"><div className="skeleton" style={{height:200}} /></div>;
  if (!show) return <div className="page-body"><div className="empty-state"><h3>Show not found</h3></div></div>;

  return (
    <>
      <div className="page-header">
        <div>
          <p className="text-sm text-muted"><Link to="/shows" style={{color:'var(--purple-600)',textDecoration:'none'}}>Shows</Link> / {show.title}</p>
          <h2>{show.title}</h2>
        </div>
        <div className="flex gap-3">
          <span className={`badge badge-${show.status}`}>{show.status}</span>
        </div>
      </div>
      <div className="page-body">
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
          <div>
            <div className="card mb-6">
              <div className="card-header"><h3>Details</h3></div>
              <div className="card-body">
                <p><strong>Section:</strong> {show.section || '—'}</p>
                <p><strong>Category:</strong> {show.category || '—'}</p>
                <p><strong>Synopsis:</strong> {show.synopsis || '—'}</p>
              </div>
            </div>
            <div className="card mb-6">
              <div className="card-header"><h3>Seasons ({seasons?.length || 0})</h3></div>
              <div className="card-body">
                {seasons?.map((season: any) => (
                  <div key={season.id} style={{padding:'8px 0',borderBottom:'1px solid var(--border-color)'}}>
                    <strong>{season.season_number === 0 ? 'Trailers' : season.title || `Season ${season.season_number}`}</strong>
                    <span className="text-sm text-muted" style={{marginLeft:8}}>{season.episode_count} episodes</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card">
              <div className="card-header"><h3>Episodes ({episodes?.total || 0})</h3></div>
              <div className="table-wrapper">
                <table>
                  <thead><tr><th>Title</th><th>Language</th><th>Content Group</th><th>Duration</th><th>Status</th></tr></thead>
                  <tbody>
                    {episodes?.items?.map((ep: any) => (
                      <tr key={ep.id}>
                        <td>{ep.title}</td>
                        <td>{ep.language}</td>
                        <td className="font-mono text-sm">{ep.content_group}</td>
                        <td>{ep.duration_seconds ? `${Math.floor(ep.duration_seconds/60)}:${(ep.duration_seconds%60).toString().padStart(2,'0')}` : '—'}</td>
                        <td><span className={`badge badge-${ep.status}`}>{ep.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div>
            <ArtworkSection ownerType="show" ownerId={showId} artwork={show.artwork || []} />
          </div>
        </div>
      </div>
    </>
  );
}

// --- Artwork Section ---
function ArtworkSection({ ownerType, ownerId, artwork }: { ownerType: string; ownerId: string; artwork: any[] }) {
  const queryClient = useQueryClient();
  const specs = [
    { type: 'poster', label: 'Poster', spec: '2:3 · ~600×900 · ≤200KB' },
    { type: 'banner', label: 'Banner', spec: '16:9 · ~1280×720 · ≤200KB' },
    { type: 'thumbnail', label: 'Thumbnail', spec: '16:9 · ~640×360 · ≤200KB' },
  ];

  const uploadMutation = useMutation({
    mutationFn: ({ file, artworkType }: { file: File; artworkType: string }) =>
      api.uploadArtwork(file, ownerType, ownerId, artworkType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['show'] });
      queryClient.invalidateQueries({ queryKey: ['validation'] });
      toast.success('Artwork uploaded');
    },
    onError: (err: any) => toast.error(err.message || 'Upload failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteArtwork(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['show'] });
      queryClient.invalidateQueries({ queryKey: ['validation'] });
      toast.success('Artwork deleted');
    },
  });

  const handleFileSelect = (artworkType: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e: any) => {
      const file = e.target.files?.[0];
      if (file) uploadMutation.mutate({ file, artworkType });
    };
    input.click();
  };

  return (
    <div className="card">
      <div className="card-header"><h3>Artwork</h3></div>
      <div className="card-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {specs.map(s => {
            const existing = artwork.find((a: any) => a.artwork_type === s.type);
            return (
              <div key={s.type} className={`artwork-card ${existing ? 'has-image' : ''}`} onClick={() => !existing && handleFileSelect(s.type)}>
                {existing ? (
                  <>
                    <img src={existing.url} alt={s.label} className="preview" loading="lazy" />
                    <div className="artwork-checks">
                      <div className="artwork-check pass">✓ Format: {existing.mime_type?.split('/')[1]?.toUpperCase()}</div>
                      <div className="artwork-check pass">✓ Dimensions: {existing.width}×{existing.height}</div>
                      <div className="artwork-check pass">✓ Size: {(existing.size_bytes / 1024).toFixed(1)} KB</div>
                    </div>
                    <div className="flex gap-2 mt-2" style={{justifyContent:'center'}}>
                      <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); handleFileSelect(s.type); }}>Replace</button>
                      <button className="btn btn-ghost btn-sm" style={{color:'var(--red-500)'}} onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(existing.id); }}>{Icons.trash}</button>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{padding:20,opacity:0.5}}>{Icons.upload}</div>
                    <div className="label">{s.label}</div>
                    <div className="spec">{s.spec}</div>
                    {uploadMutation.isPending && <div className="spinner spinner-dark mt-2" />}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// --- Episodes Page ---
function EpisodesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [langFilter, setLangFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const searchTimeout = useRef<number | undefined>(undefined);
  // Removed unused queryClient

  useEffect(() => {
    clearTimeout(searchTimeout.current);
    searchTimeout.current = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(searchTimeout.current);
  }, [search]);

  const { data, isLoading } = useQuery({
    queryKey: ['episodes', { page, search: debouncedSearch, language: langFilter, status: statusFilter }],
    queryFn: () => api.listEpisodes({ page, page_size: 20, search: debouncedSearch || undefined, language: langFilter || undefined, status: statusFilter || undefined }),
  });

  const totalPages = Math.ceil((data?.total || 0) / 20);

  return (
    <>
      <div className="page-header">
        <div><h2>Episodes</h2><p>{data?.total || 0} episodes</p></div>
      </div>
      <div className="page-body">
        <div className="card">
          <div className="toolbar">
            <div className="search-input">
              {Icons.search}
              <input placeholder="Search episodes..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
            </div>
            <select className="filter-select" value={langFilter} onChange={e => { setLangFilter(e.target.value); setPage(1); }}>
              <option value="">All Languages</option>
              <option value="English">English</option>
              <option value="Hindi">Hindi</option>
              <option value="Tamil">Tamil</option>
              <option value="Telugu">Telugu</option>
            </select>
            <select className="filter-select" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All Status</option>
              <option value="published">Published</option>
              <option value="draft">Draft</option>
            </select>
          </div>
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Title</th><th>Show</th><th>Season</th><th>Language</th><th>Content Group</th><th>Duration</th><th>Status</th></tr></thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}><td colSpan={7}><div className="skeleton" style={{height:20}} /></td></tr>
                  ))
                ) : data?.items?.length ? (
                  data.items.map((ep: any) => (
                    <tr key={ep.id}>
                      <td style={{maxWidth:200}} className="truncate">{ep.title}</td>
                      <td>{ep.show_title || '—'}</td>
                      <td>{ep.season_number != null ? (ep.season_number === 0 ? 'Trailer' : `S${ep.season_number}`) : '—'}</td>
                      <td>{ep.language}</td>
                      <td className="font-mono text-sm">{ep.content_group}</td>
                      <td>{ep.duration_seconds ? `${Math.floor(ep.duration_seconds/60)}:${(ep.duration_seconds%60).toString().padStart(2,'0')}` : <span style={{color:'var(--red-500)'}}>Missing</span>}</td>
                      <td><span className={`badge badge-${ep.status}`}>{ep.status}</span></td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={7}><div className="empty-state"><h3>No episodes found</h3></div></td></tr>
                )}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="pagination">
              <span className="pagination-info">Page {page} of {totalPages}</span>
              <div className="pagination-controls">
                <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
                <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// --- Validation Page ---
function ValidationPage() {
  const { data, isLoading } = useQuery({ queryKey: ['validation'], queryFn: () => api.getValidationReport() });

  const categories = ['content', 'artwork', 'languages', 'publishing'];

  return (
    <>
      <div className="page-header">
        <div><h2>Validation Report</h2><p>Publishing readiness checks</p></div>
        {data && (
          <div className={`health-badge ${data.ready ? 'ready' : 'blocked'}`}>
            <span className={`health-dot ${data.ready ? 'ready' : 'blocked'}`} />
            {data.ready ? 'Ready to Publish' : `${data.blocking_count} Blocking Issues`}
          </div>
        )}
      </div>
      <div className="page-body">
        {isLoading ? (
          <div className="skeleton" style={{height:200}} />
        ) : data?.issues?.length ? (
          categories.map(cat => {
            const catIssues = data.issues.filter((i: any) => i.category === cat);
            if (!catIssues.length) return null;
            return (
              <div key={cat} className="card mb-6">
                <div className="card-header">
                  <h3 style={{ textTransform: 'capitalize' }}>{cat}</h3>
                  <span className="badge badge-blocking">{catIssues.length}</span>
                </div>
                <div className="card-body">
                  <div className="issue-list">
                    {catIssues.map((issue: any, idx: number) => (
                      <div key={idx} className={`issue-item ${issue.severity}`}>
                        <div style={{color: issue.severity === 'blocking' ? 'var(--red-500)' : 'var(--amber-500)', flexShrink:0, marginTop:2}}>
                          {Icons.alert}
                        </div>
                        <div className="issue-content">
                          <div className="issue-title">{issue.message}</div>
                          {issue.entity_name && <div className="issue-entity">{issue.entity_type}: {issue.entity_name}</div>}
                          <div className="issue-action">💡 {issue.suggested_action}</div>
                        </div>
                        <span className={`badge badge-${issue.severity}`}>{issue.severity}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="card">
            <div className="card-body">
              <div className="empty-state">
                <div style={{fontSize:48}}>✅</div>
                <h3>All Checks Passed</h3>
                <p>Content is ready for catalogue publication.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// --- Publish Page ---
function PublishPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { data: validation, isLoading: valLoading } = useQuery({ queryKey: ['validation'], queryFn: () => api.getValidationReport() });
  const { data: runs } = useQuery({ queryKey: ['publish-runs'], queryFn: () => api.listPublishRuns(20) });
  const [showConfirm, setShowConfirm] = useState(false);
  const [receipt, setReceipt] = useState<any>(null);
  const [publishing, setPublishing] = useState(false);
  const [stages, setStages] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin';

  const handlePublish = async () => {
    setShowConfirm(false);
    setPublishing(true);
    setError(null);
    setReceipt(null);
    setStages([
      { name: 'Validation', status: 'running' },
    ]);

    try {
      // Simulate stage progression for UX
      await new Promise(r => setTimeout(r, 300));
      setStages(s => [...s.map(st => st.name === 'Validation' ? {...st, status: 'success'} : st), { name: 'Catalogue Build', status: 'running' }]);
      await new Promise(r => setTimeout(r, 200));
      setStages(s => [...s.map(st => st.name === 'Catalogue Build' ? {...st, status: 'success'} : st), { name: 'Language Grouping', status: 'running' }]);
      await new Promise(r => setTimeout(r, 150));
      setStages(s => [...s.map(st => st.name === 'Language Grouping' ? {...st, status: 'success'} : st), { name: 'Deterministic Ordering', status: 'running' }]);

      const result = await api.publish();

      setStages(result.stages || [
        { name: 'Validation', status: 'success' },
        { name: 'Catalogue Build', status: 'success' },
        { name: 'Language Grouping', status: 'success' },
        { name: 'Deterministic Ordering', status: 'success' },
        { name: 'Integrity Hash', status: 'success' },
        { name: 'Immutable Storage', status: 'success' },
        { name: 'Atomic Activation', status: 'success' },
        { name: 'Run Recorded', status: 'success' },
      ]);
      setReceipt(result);
      queryClient.invalidateQueries({ queryKey: ['validation'] });
      queryClient.invalidateQueries({ queryKey: ['publish-runs'] });
      toast.success('Catalogue published successfully!');
    } catch (err: any) {
      setError(err.message || 'Publication failed');
      setStages(s => [...s.filter(st => st.status === 'success'), { name: 'Failed', status: 'failed', message: err.message }]);
      toast.error(err.message || 'Publication failed');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <div><h2>Catalogue Publishing</h2><p>Manage catalogue publication pipeline</p></div>
      </div>
      <div className="page-body">
        {!isAdmin ? (
          <div className="card">
            <div className="card-body">
              <div className="empty-state">
                <div style={{opacity:0.5}}>{Icons.lock}</div>
                <h3>Publishing — Admin Only</h3>
                <p>You need administrator privileges to publish catalogues.</p>
                <span className="badge badge-editor">Editor Access</span>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Health */}
            <div className="card mb-6">
              <div className="card-header">
                <h3>Catalogue Health</h3>
                {validation && (
                  <div className={`health-badge ${validation.ready ? 'ready' : 'blocked'}`}>
                    <span className={`health-dot ${validation.ready ? 'ready' : 'blocked'}`} />
                    {validation.ready ? 'Ready to Publish' : 'Blocked'}
                  </div>
                )}
              </div>
              <div className="card-body">
                {valLoading ? (
                  <div className="skeleton" style={{height:40}} />
                ) : validation?.ready ? (
                  <div>
                    <p style={{color:'#16a34a',fontWeight:500,marginBottom:16}}>✅ All validation checks passed</p>
                    <button className="btn btn-primary btn-lg" onClick={() => setShowConfirm(true)} disabled={publishing}>
                      {publishing ? <><span className="spinner" /> Publishing...</> : '🚀 Publish Catalogue'}
                    </button>
                  </div>
                ) : (
                  <div>
                    <p style={{color:'var(--red-500)',marginBottom:8}}>{validation?.blocking_count} issue{validation?.blocking_count !== 1 ? 's' : ''} must be resolved before publishing.</p>
                    <Link to="/validation" className="btn btn-secondary">Review Issues</Link>
                  </div>
                )}
              </div>
            </div>

            {/* Active pipeline / receipt */}
            {(stages.length > 0 || receipt) && (
              <div className="card mb-6">
                <div className="card-header">
                  <h3>{receipt ? 'Catalogue Published' : error ? 'Publication Failed' : 'Publishing...'}</h3>
                </div>
                <div className="card-body">
                  <div className="publish-stages mb-6">
                    {stages.map((stage: any, idx: number) => (
                      <div key={idx} className={`publish-stage ${stage.status}`}>
                        {stage.status === 'success' ? '✓' : stage.status === 'failed' ? '✗' : stage.status === 'running' ? <span className="spinner spinner-dark" /> : '○'}
                        <span>{stage.name}</span>
                        {stage.message && <span className="text-muted text-sm" style={{marginLeft:8}}>{stage.message}</span>}
                      </div>
                    ))}
                  </div>
                  {receipt && (
                    <div className="publish-receipt">
                      <div className="receipt-grid">
                        <div className="receipt-item"><div className="label">Version</div><div className="value">v{receipt.version}</div></div>
                        <div className="receipt-item"><div className="label">Shows</div><div className="value">{receipt.shows_count}</div></div>
                        <div className="receipt-item"><div className="label">Episodes</div><div className="value">{receipt.episodes_count}</div></div>
                        <div className="receipt-item"><div className="label">Language Groups</div><div className="value">{receipt.language_group_count}</div></div>
                        <div className="receipt-item"><div className="label">Duration</div><div className="value">{receipt.duration_ms}ms</div></div>
                        <div className="receipt-item"><div className="label">Triggered By</div><div className="value">{receipt.triggered_by}</div></div>
                      </div>
                      <div className="receipt-item"><div className="label">SHA-256</div><div className="value font-mono" style={{fontSize:'0.75rem'}}>{receipt.catalogue_hash}</div></div>
                    </div>
                  )}
                  {error && !receipt && (
                    <div style={{background:'#fee2e2',padding:16,borderRadius:8,color:'#dc2626'}}>
                      <strong>Publication failed</strong>
                      <p>{error}</p>
                      <p style={{marginTop:8,fontSize:'0.8rem',color:'#64748b'}}>The previous catalogue remains live.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* History */}
            <div className="card">
              <div className="card-header"><h3>Publish History</h3></div>
              <div className="table-wrapper">
                <table>
                  <thead><tr><th>Status</th><th>Version</th><th>Shows</th><th>Episodes</th><th>Duration</th><th>By</th><th>Date</th></tr></thead>
                  <tbody>
                    {runs?.items?.length ? runs.items.map((run: any) => (
                      <tr key={run.id}>
                        <td><span className={`badge badge-${run.status === 'success' ? 'success' : 'error'}`}>{run.status}</span></td>
                        <td>{run.catalogue_hash ? `${run.catalogue_hash.substring(0, 8)}...` : '—'}</td>
                        <td>{run.shows_count ?? '—'}</td>
                        <td>{run.episodes_count ?? '—'}</td>
                        <td>{run.duration_ms ? `${run.duration_ms}ms` : '—'}</td>
                        <td>{run.triggered_by_email || '—'}</td>
                        <td>{new Date(run.created_at).toLocaleString()}</td>
                      </tr>
                    )) : (
                      <tr><td colSpan={7}><div className="empty-state"><p>No publish runs yet</p></div></td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* Publish Confirmation Modal */}
        {showConfirm && (
          <div className="modal-overlay" onClick={() => setShowConfirm(false)}>
            <div className="modal" onClick={e => e.stopPropagation()}>
              <div className="modal-header"><h3>Publish Catalogue?</h3></div>
              <div className="modal-body">
                <p>This will make the validated catalogue available to Peblo TV viewers.</p>
                <p style={{marginTop:12,color:'var(--text-secondary)',fontSize:'0.85rem'}}>The currently live catalogue will remain available until activation succeeds.</p>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setShowConfirm(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={handlePublish}>🚀 Publish</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// --- Main App ---
function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = [
    { path: '/', icon: Icons.dashboard, label: 'Dashboard' },
    { path: '/shows', icon: Icons.shows, label: 'Shows' },
    { path: '/episodes', icon: Icons.episodes, label: 'Episodes' },
    { path: '/validation', icon: Icons.alert, label: 'Validation' },
    { path: '/publish', icon: Icons.publish, label: 'Publishing' },
  ];

  return (
    <div className="app-layout">
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <h1>🎬 Peblo Studio</h1>
          <small>Content Operations</small>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path)) ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{user?.email?.charAt(0).toUpperCase()}</div>
            <div className="user-details">
              <div className="name">{user?.email}</div>
              <div className="role">{user?.role}</div>
            </div>
            <button className="btn btn-ghost" onClick={logout} title="Sign out" style={{color:'var(--gray-400)'}}>{Icons.logout}</button>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <div style={{padding:'12px 24px',display:'none'}} className="mobile-menu-btn-wrapper">
          <button className="mobile-menu-btn" onClick={() => setSidebarOpen(true)}>{Icons.menu}</button>
        </div>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/shows" element={<ShowsPage />} />
          <Route path="/shows/:id" element={<ShowDetailPage />} />
          <Route path="/episodes" element={<EpisodesPage />} />
          <Route path="/validation" element={<ValidationPage />} />
          <Route path="/publish" element={<PublishPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const { user, loading } = useAuth();
  if (loading) return <div style={{display:'flex',alignItems:'center',justifyContent:'center',minHeight:'100vh'}}><span className="spinner spinner-dark" style={{width:40,height:40}} /></div>;
  if (!user) return <LoginPage />;
  return <AppLayout />;
}
