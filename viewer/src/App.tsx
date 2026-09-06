import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from './api';

function App() {
  const [search, setSearch] = useState('');
  
  const { data, isLoading } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => api.getCatalogue()
  });

  const { data: searchData } = useQuery({
    queryKey: ['search', search],
    queryFn: () => api.searchCatalogue(search),
    enabled: search.length > 2
  });

  const displayData = search.length > 2 && searchData ? { sections: [{ name: 'Search Results', shows: searchData.results }] } : data;

  return (
    <div>
      <nav className="navbar">
        <div className="navbar-brand">Peblo TV</div>
        <div className="search-bar">
          <input 
            type="text" 
            className="search-input" 
            placeholder="Search shows..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </nav>

      <main className="main-content">
        {!search && (
          <div className="hero-banner" style={{ backgroundImage: `url('https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&q=80&w=1200')` }}>
            <div className="hero-overlay"></div>
            <div className="hero-content">
              <h1 className="hero-title">Welcome to Peblo TV</h1>
              <p style={{ marginBottom: 16, fontSize: '1.2rem', color: '#e0e0e0', maxWidth: 600 }}>
                Discover amazing animation, fun educational content, and exciting adventures for everyone!
              </p>
              <button className="btn-play">▶ Play Now</button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="empty-state">Loading amazing content...</div>
        ) : !displayData?.sections?.length ? (
           <div className="empty-state">No content found. Please check back later!</div>
        ) : (
          displayData.sections.map((section: any, idx: number) => (
            <div key={idx} style={{ marginBottom: 48 }}>
              <h2 className="section-title">{section.name || section.section}</h2>
              <div className="show-grid">
                {section.shows?.map((show: any) => (
                  <div key={show.id} className="show-card">
                    <img 
                      src={show.artwork?.poster || 'https://via.placeholder.com/400x600/333/fff?text=No+Poster'} 
                      alt={show.title} 
                      className="show-poster" 
                      loading="lazy"
                    />
                    <div className="show-info">
                      <div className="show-title">{show.title}</div>
                      <div className="show-meta">
                        {show.category} • {show.languages?.join(', ')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}

export default App;
