import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from './api';

type Language = {
  language: string;
  video_url: string;
};

type Episode = {
  content_group: string;
  title: string;
  synopsis: string;
  duration_seconds: number;
  thumbnail: string | null;
  languages: Language[];
};

type Season = {
  season_number: number;
  title: string;
  episodes: Episode[];
};

type Show = {
  id: string;
  title: string;
  slug: string;
  synopsis: string;
  category: string;
  artwork: {
    banner?: string | null;
    poster?: string | null;
  };
  seasons: Season[];
};

type Section = {
  section: string;
  shows: Show[];
};

type Catalogue = {
  version: number;
  generated_at: string;
  catalogue_hash: string;
  sections: Section[];
};

function formatDuration(seconds: number) {
  if (!seconds) return '';

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  }

  if (remainingSeconds === 0) {
    return `${minutes} min`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

function App() {
  const [search, setSearch] = useState('');
  const [selectedShow, setSelectedShow] = useState<Show | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery<Catalogue>({
    queryKey: ['catalogue'],
    queryFn: () => api.getCatalogue(),
  });

  const catalogue = data;

  /*
   * Flatten the catalogue so filtering stays simple and deterministic.
   */
  const allShows = useMemo(() => {
    if (!catalogue?.sections) return [];

    return catalogue.sections.flatMap((section) => section.shows || []);
  }, [catalogue]);

  /*
   * Search across:
   * - show title
   * - show synopsis
   * - category
   * - episode title
   * - episode synopsis
   */
  const filteredSections = useMemo(() => {
    if (!catalogue?.sections) return [];

    const query = search.trim().toLowerCase();

    if (!query) {
      return catalogue.sections;
    }

    return catalogue.sections
      .map((section) => {
        const shows = section.shows.filter((show) => {
          const showMatches =
            show.title.toLowerCase().includes(query) ||
            show.category.toLowerCase().includes(query) ||
            show.synopsis.toLowerCase().includes(query);

          const episodeMatches = show.seasons.some((season) =>
            season.episodes.some(
              (episode) =>
                episode.title.toLowerCase().includes(query) ||
                episode.synopsis.toLowerCase().includes(query),
            ),
          );

          return showMatches || episodeMatches;
        });

        return {
          ...section,
          shows,
        };
      })
      .filter((section) => section.shows.length > 0);
  }, [catalogue, search]);

  /*
   * Pick a strong hero show.
   * Prefer Featured, otherwise use the first available show.
   */
  const heroShow = useMemo(() => {
    if (!allShows.length) return null;

    const featuredSection = catalogue?.sections?.find(
      (section) => section.section === 'Featured',
    );

    return featuredSection?.shows?.[0] || allShows[0];
  }, [allShows, catalogue]);

  /*
   * When a show is selected, show the details page.
   */
  if (selectedShow) {
    return (
      <ShowDetails
        show={selectedShow}
        selectedLanguage={selectedLanguage}
        setSelectedLanguage={setSelectedLanguage}
        onBack={() => {
          setSelectedShow(null);
          setSelectedLanguage(null);
        }}
      />
    );
  }

  return (
    <div className="app">
      <style>{styles}</style>

      {/* NAVBAR */}
      <header className="navbar">
        <div className="navbar-inner">
          <button
            className="brand"
            onClick={() => {
              setSelectedShow(null);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          >
            <span className="brand-mark">P</span>
            <span>Peblo TV</span>
          </button>

          <div className="search-wrapper">
            <span className="search-icon">⌕</span>

            <input
              type="search"
              className="search-input"
              placeholder="Search shows, episodes..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />

            {search && (
              <button
                className="search-clear"
                onClick={() => setSearch('')}
                aria-label="Clear search"
              >
                ×
              </button>
            )}
          </div>
        </div>
      </header>

      {/* HERO */}
      {!search && heroShow && (
        <section className="hero">
          <div
            className="hero-background"
            style={{
              backgroundImage: `url("${heroShow.artwork?.banner ||
                heroShow.artwork?.poster ||
                ''
                }")`,
            }}
          />

          <div className="hero-gradient" />

          <div className="hero-content">
            <div className="hero-badge">
              <span>✦</span>
              Featured on Peblo
            </div>

            <h1>{heroShow.title}</h1>

            <div className="hero-meta">
              <span>{heroShow.category}</span>
              <span>•</span>
              <span>Kids & Family</span>
            </div>

            <p>{heroShow.synopsis}</p>

            <div className="hero-actions">
              <button
                className="primary-button"
                onClick={() => setSelectedShow(heroShow)}
              >
                <span>▶</span>
                Explore Show
              </button>

              <button
                className="secondary-button"
                onClick={() => setSelectedShow(heroShow)}
              >
                More Info
              </button>
            </div>
          </div>
        </section>
      )}

      {/* MAIN */}
      <main className="main-content">
        {search && (
          <div className="search-heading">
            <span>Search results for</span>
            <strong>"{search}"</strong>
          </div>
        )}

        {isLoading && (
          <div className="loading-grid">
            {Array.from({ length: 8 }).map((_, index) => (
              <div className="skeleton-card" key={index}>
                <div className="skeleton-poster" />
                <div className="skeleton-line" />
                <div className="skeleton-line small" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="state-card">
            <div className="state-icon">⚠</div>
            <h2>Something went wrong</h2>
            <p>
              We couldn't load Peblo TV right now. Please refresh and try
              again.
            </p>
          </div>
        )}

        {!isLoading &&
          !isError &&
          filteredSections.length === 0 && (
            <div className="state-card">
              <div className="state-icon">⌕</div>
              <h2>No results found</h2>
              <p>
                Try searching for another show, episode, or category.
              </p>

              <button
                className="primary-button"
                onClick={() => setSearch('')}
              >
                Browse Peblo TV
              </button>
            </div>
          )}

        {!isLoading &&
          !isError &&
          filteredSections.map((section) => (
            <section
              className="content-section"
              key={section.section}
            >
              <div className="section-header">
                <div>
                  <h2>{section.section}</h2>
                  <p>
                    {section.shows.length}{' '}
                    {section.shows.length === 1 ? 'show' : 'shows'}
                  </p>
                </div>
              </div>

              <div className="show-row">
                {section.shows.map((show) => (
                  <button
                    className="show-card"
                    key={show.id}
                    onClick={() => setSelectedShow(show)}
                  >
                    <div className="poster-wrapper">
                      <img
                        src={
                          show.artwork?.poster ||
                          show.artwork?.banner ||
                          ''
                        }
                        alt={show.title}
                        className="show-poster"
                        loading="lazy"
                      />

                      <div className="poster-overlay">
                        <span className="play-circle">▶</span>
                      </div>

                      <div className="card-category">
                        {show.category}
                      </div>
                    </div>

                    <div className="show-card-info">
                      <h3>{show.title}</h3>

                      <p>
                        {show.seasons.filter(
                          (season) => season.season_number !== 0,
                        ).length}{' '}
                        {show.seasons.length === 1
                          ? 'season'
                          : 'seasons'}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          ))}
      </main>

      <footer className="footer">
        <div className="footer-brand">
          <span className="brand-mark">P</span>
          <span>Peblo TV</span>
        </div>

        <p>
          A child-friendly learning and entertainment playground.
        </p>

        <span className="footer-version">
          Catalogue v{catalogue?.version ?? '—'}
        </span>
      </footer>
    </div>
  );
}


function ShowDetails({
  show,
  selectedLanguage,
  setSelectedLanguage,
  onBack,
}: {
  show: Show;
  selectedLanguage: string | null;
  setSelectedLanguage: (language: string | null) => void;
  onBack: () => void;
}) {
  const normalSeasons = show.seasons.filter(
    (season) => season.season_number !== 0,
  );

  const trailerSeason = show.seasons.find(
    (season) => season.season_number === 0,
  );

  const availableLanguages = Array.from(
    new Set(
      show.seasons.flatMap((season) =>
        season.episodes.flatMap((episode) =>
          episode.languages.map((language) => language.language),
        ),
      ),
    ),
  ).sort();

  return (
    <div className="details-page">
      <style>{styles}</style>

      {/* DETAILS HERO */}
      <section className="details-hero">
        <div
          className="details-background"
          style={{
            backgroundImage: `url("${show.artwork?.banner ||
              show.artwork?.poster ||
              ''
              }")`,
          }}
        />

        <div className="details-gradient" />

        <button className="back-button" onClick={onBack}>
          ← Back to Peblo TV
        </button>

        <div className="details-content">
          <div className="details-poster-wrap">
            <img
              src={show.artwork?.poster || ''}
              alt={show.title}
              className="details-poster"
            />
          </div>

          <div className="details-info">
            <div className="details-category">
              {show.category}
            </div>

            <h1>{show.title}</h1>

            <p className="details-synopsis">
              {show.synopsis}
            </p>

            <div className="details-stats">
              <span>
                {normalSeasons.length}{' '}
                {normalSeasons.length === 1
                  ? 'Season'
                  : 'Seasons'}
              </span>

              <span>•</span>

              <span>
                {normalSeasons.reduce(
                  (total, season) =>
                    total + season.episodes.length,
                  0,
                )}{' '}
                Episodes
              </span>

              {availableLanguages.length > 0 && (
                <>
                  <span>•</span>
                  <span>
                    {availableLanguages.length}{' '}
                    {availableLanguages.length === 1
                      ? 'Language'
                      : 'Languages'}
                  </span>
                </>
              )}
            </div>

            {availableLanguages.length > 0 && (
              <div className="language-filter">
                <span>Language:</span>

                <button
                  className={
                    selectedLanguage === null
                      ? 'language-pill active'
                      : 'language-pill'
                  }
                  onClick={() => setSelectedLanguage(null)}
                >
                  All
                </button>

                {availableLanguages.map((language) => (
                  <button
                    key={language}
                    className={
                      selectedLanguage === language
                        ? 'language-pill active'
                        : 'language-pill'
                    }
                    onClick={() =>
                      setSelectedLanguage(language)
                    }
                  >
                    {language}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* EPISODES */}
      <main className="details-main">
        {normalSeasons.map((season) => (
          <section className="episode-section" key={season.season_number}>
            <div className="episode-section-heading">
              <div>
                <span className="eyebrow">COLLECTION</span>
                <h2>{season.title}</h2>
              </div>

              <span className="episode-count">
                {season.episodes.length}{' '}
                {season.episodes.length === 1
                  ? 'episode'
                  : 'episodes'}
              </span>
            </div>

            <div className="episode-list">
              {season.episodes.map((episode, index) => {
                const languages = selectedLanguage
                  ? episode.languages.filter(
                    (language) =>
                      language.language === selectedLanguage,
                  )
                  : episode.languages;

                return (
                  <article
                    className="episode-card"
                    key={episode.content_group}
                  >
                    <div className="episode-number">
                      {String(index + 1).padStart(2, '0')}
                    </div>

                    <div className="episode-thumb">
                      {episode.thumbnail ? (
                        <img
                          src={episode.thumbnail}
                          alt={episode.title}
                          loading="lazy"
                        />
                      ) : (
                        <div className="episode-thumb-placeholder">
                          <span>▶</span>
                        </div>
                      )}

                      <div className="episode-play-overlay">
                        <span>▶</span>
                      </div>
                    </div>

                    <div className="episode-info">
                      <h3>{episode.title}</h3>

                      <p>{episode.synopsis}</p>

                      <div className="episode-meta">
                        {episode.duration_seconds > 0 && (
                          <span>
                            ⏱{' '}
                            {formatDuration(
                              episode.duration_seconds,
                            )}
                          </span>
                        )}

                        <span>
                          {episode.languages.length}{' '}
                          {episode.languages.length === 1
                            ? 'language'
                            : 'languages'}
                        </span>
                      </div>
                    </div>

                    <div className="episode-actions">
                      {languages.map((language) => (
                        <button
                          className="play-language"
                          key={language.language}
                          onClick={() =>
                            window.open(
                              language.video_url,
                              '_blank',
                              'noopener,noreferrer',
                            )
                          }
                          title={`Play in ${language.language}`}
                        >
                          ▶ {language.language}
                        </button>
                      ))}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}

        {/* TRAILERS / SEASON 0 */}
        {trailerSeason && (
          <section className="trailer-section">
            <div className="episode-section-heading">
              <div>
                <span className="eyebrow">BONUS</span>
                <h2>Trailers</h2>
              </div>
            </div>

            <div className="episode-list">
              {trailerSeason.episodes.map((episode) => (
                <article
                  className="episode-card trailer-card"
                  key={episode.content_group}
                >
                  <div className="episode-thumb">
                    {episode.thumbnail ? (
                      <img
                        src={episode.thumbnail}
                        alt={episode.title}
                        loading="lazy"
                      />
                    ) : (
                      <div className="episode-thumb-placeholder trailer">
                        <span>▶</span>
                      </div>
                    )}
                  </div>

                  <div className="episode-info">
                    <span className="trailer-label">
                      TRAILER
                    </span>

                    <h3>{episode.title}</h3>

                    <p>{episode.synopsis}</p>
                  </div>

                  <div className="episode-actions">
                    {episode.languages.map((language) => (
                      <button
                        className="play-language"
                        key={language.language}
                        onClick={() =>
                          window.open(
                            language.video_url,
                            '_blank',
                            'noopener,noreferrer',
                          )
                        }
                      >
                        ▶ Watch
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        <div className="details-back">
          <button className="secondary-button" onClick={onBack}>
            ← Back to all shows
          </button>
        </div>
      </main>
    </div>
  );
}


const styles = `
  * {
    box-sizing: border-box;
  }

  html {
    scroll-behavior: smooth;
  }

  body {
    margin: 0;
    background: #0b0d12;
    color: #f8fafc;
    font-family:
      Inter,
      ui-sans-serif,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif;
  }

  button,
  input {
    font: inherit;
  }

  button {
    border: 0;
  }

  .app {
    min-height: 100vh;
    background:
      radial-gradient(
        circle at 50% -20%,
        rgba(255, 124, 72, 0.08),
        transparent 35%
      ),
      #0b0d12;
  }

  /* NAVBAR */

  .navbar {
    position: sticky;
    top: 0;
    z-index: 50;
    height: 72px;
    background: rgba(11, 13, 18, 0.92);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid rgba(255,255,255,0.07);
  }

  .navbar-inner {
    width: min(1400px, calc(100% - 48px));
    height: 100%;
    margin: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    background: none;
    color: white;
    font-size: 22px;
    font-weight: 800;
    cursor: pointer;
    letter-spacing: -0.5px;
  }

  .brand-mark {
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    border-radius: 10px;
    background: linear-gradient(135deg, #ff8a5b, #ff5f45);
    color: white;
    font-weight: 900;
    box-shadow: 0 8px 24px rgba(255, 100, 70, 0.25);
  }

  .search-wrapper {
    position: relative;
    width: min(380px, 45vw);
  }

  .search-input {
    width: 100%;
    height: 42px;
    border-radius: 22px;
    border: 1px solid rgba(255,255,255,0.13);
    background: rgba(255,255,255,0.06);
    color: white;
    padding: 0 42px;
    outline: none;
    transition: 0.2s ease;
  }

  .search-input:focus {
    border-color: rgba(255,138,91,0.7);
    background: rgba(255,255,255,0.09);
    box-shadow: 0 0 0 4px rgba(255,138,91,0.08);
  }

  .search-input::placeholder {
    color: #8c929e;
  }

  .search-icon {
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-52%);
    color: #9ba1ad;
    font-size: 21px;
    z-index: 2;
  }

  .search-clear {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: rgba(255,255,255,0.1);
    color: white;
    cursor: pointer;
  }

  /* HERO */

  .hero {
    position: relative;
    min-height: 570px;
    overflow: hidden;
    display: flex;
    align-items: flex-end;
  }

  .hero-background {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    transform: scale(1.02);
    filter: saturate(1.08);
  }

  .hero-gradient {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(
        90deg,
        rgba(7,9,13,0.98) 0%,
        rgba(7,9,13,0.86) 32%,
        rgba(7,9,13,0.35) 70%,
        rgba(7,9,13,0.65) 100%
      ),
      linear-gradient(
        0deg,
        #0b0d12 0%,
        transparent 45%
      );
  }

  .hero-content {
    position: relative;
    z-index: 2;
    width: min(1400px, calc(100% - 48px));
    margin: 0 auto;
    padding: 80px 0 90px;
    max-width: 750px;
  }

  .hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    color: #ffd8ca;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }

  .hero h1 {
    margin: 18px 0 10px;
    font-size: clamp(44px, 6vw, 76px);
    line-height: 0.98;
    letter-spacing: -3px;
  }

  .hero-meta {
    display: flex;
    gap: 10px;
    align-items: center;
    color: #cbd0d9;
    font-size: 15px;
    font-weight: 600;
  }

  .hero p {
    max-width: 650px;
    color: #c5cad3;
    line-height: 1.7;
    font-size: 17px;
    margin: 20px 0 28px;
  }

  .hero-actions {
    display: flex;
    gap: 12px;
  }

  .primary-button,
  .secondary-button {
    min-height: 44px;
    padding: 0 20px;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 750;
    transition: 0.2s ease;
  }

  .primary-button {
    background: linear-gradient(135deg, #ff8a5b, #ff654a);
    color: white;
    box-shadow: 0 10px 28px rgba(255,100,70,0.2);
  }

  .primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 34px rgba(255,100,70,0.3);
  }

  .secondary-button {
    background: rgba(255,255,255,0.1);
    color: white;
    border: 1px solid rgba(255,255,255,0.12);
  }

  .secondary-button:hover {
    background: rgba(255,255,255,0.16);
    transform: translateY(-2px);
  }

  /* CONTENT */

  .main-content {
    width: min(1400px, calc(100% - 48px));
    margin: auto;
    padding: 28px 0 80px;
  }

  .content-section {
    margin-bottom: 52px;
  }

  .section-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 18px;
  }

  .section-header h2 {
    margin: 0;
    font-size: 25px;
    letter-spacing: -0.6px;
  }

  .section-header p {
    margin: 5px 0 0;
    color: #777e8c;
    font-size: 13px;
  }

  .show-row {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 18px;
  }

  .show-card {
    padding: 0;
    text-align: left;
    color: white;
    background: none;
    cursor: pointer;
    min-width: 0;
  }

  .poster-wrapper {
    position: relative;
    aspect-ratio: 2 / 3;
    overflow: hidden;
    border-radius: 14px;
    background: #171a21;
    box-shadow: 0 12px 35px rgba(0,0,0,0.28);
  }

  .show-poster {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
    transition:
      transform 0.35s ease,
      filter 0.35s ease;
  }

  .show-card:hover .show-poster {
    transform: scale(1.045);
    filter: brightness(0.72);
  }

  .poster-overlay {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgba(0,0,0,0.15);
    opacity: 0;
    transition: 0.25s ease;
  }

  .show-card:hover .poster-overlay {
    opacity: 1;
  }

  .play-circle {
    width: 58px;
    height: 58px;
    display: grid;
    place-items: center;
    padding-left: 3px;
    border-radius: 50%;
    background: rgba(255,255,255,0.94);
    color: #151820;
    font-size: 20px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.3);
  }

  .card-category {
    position: absolute;
    left: 10px;
    bottom: 10px;
    padding: 5px 8px;
    border-radius: 7px;
    background: rgba(0,0,0,0.62);
    backdrop-filter: blur(8px);
    color: #f2f3f5;
    font-size: 10px;
    font-weight: 700;
  }

  .show-card-info {
    padding: 11px 3px 0;
  }

  .show-card-info h3 {
    margin: 0;
    font-size: 16px;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .show-card-info p {
    margin: 5px 0 0;
    color: #777e8c;
    font-size: 12px;
  }

  /* SEARCH */

  .search-heading {
    padding: 25px 0 32px;
    display: flex;
    gap: 8px;
    align-items: baseline;
    color: #858c99;
  }

  .search-heading strong {
    color: white;
    font-size: 25px;
  }

  /* STATES */

  .state-card {
    min-height: 380px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    text-align: center;
    padding: 40px;
  }

  .state-icon {
    width: 70px;
    height: 70px;
    display: grid;
    place-items: center;
    border-radius: 22px;
    background: rgba(255,255,255,0.06);
    color: #ff8962;
    font-size: 32px;
    margin-bottom: 20px;
  }

  .state-card h2 {
    margin: 0 0 8px;
  }

  .state-card p {
    max-width: 420px;
    color: #7f8795;
    line-height: 1.6;
    margin-bottom: 24px;
  }

  /* SKELETON */

  .loading-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 18px;
  }

  .skeleton-card {
    min-width: 0;
  }

  .skeleton-poster {
    aspect-ratio: 2 / 3;
    border-radius: 14px;
    background:
      linear-gradient(
        90deg,
        #151820 25%,
        #1d212a 50%,
        #151820 75%
      );
    background-size: 200% 100%;
    animation: skeleton 1.5s infinite;
  }

  .skeleton-line {
    width: 75%;
    height: 15px;
    margin: 12px 4px 0;
    border-radius: 6px;
    background: #171a21;
  }

  .skeleton-line.small {
    width: 45%;
    height: 10px;
    margin-top: 7px;
  }

  @keyframes skeleton {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  /* DETAILS */

  .details-page {
    min-height: 100vh;
    background: #0b0d12;
  }

  .details-hero {
    position: relative;
    min-height: 600px;
    overflow: hidden;
    display: flex;
    align-items: flex-end;
  }

  .details-background {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    filter: saturate(1.08);
  }

  .details-gradient {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(
        90deg,
        rgba(7,9,13,0.98) 0%,
        rgba(7,9,13,0.87) 40%,
        rgba(7,9,13,0.3) 100%
      ),
      linear-gradient(
        0deg,
        #0b0d12 0%,
        transparent 50%
      );
  }

  .back-button {
    position: absolute;
    z-index: 5;
    top: 24px;
    left: max(24px, calc((100% - 1400px) / 2));
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(0,0,0,0.45);
    border: 1px solid rgba(255,255,255,0.13);
    color: white;
    cursor: pointer;
    backdrop-filter: blur(12px);
  }

  .back-button:hover {
    background: rgba(255,255,255,0.12);
  }

  .details-content {
    position: relative;
    z-index: 2;
    width: min(1400px, calc(100% - 48px));
    margin: auto;
    padding: 100px 0 80px;
    display: flex;
    gap: 42px;
    align-items: flex-end;
  }

  .details-poster-wrap {
    width: 230px;
    flex: 0 0 230px;
  }

  .details-poster {
    display: block;
    width: 100%;
    aspect-ratio: 2 / 3;
    object-fit: cover;
    border-radius: 16px;
    box-shadow: 0 25px 70px rgba(0,0,0,0.45);
  }

  .details-info {
    max-width: 720px;
    padding-bottom: 8px;
  }

  .details-category {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 7px;
    background: rgba(255,255,255,0.09);
    color: #ffae91;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .details-info h1 {
    margin: 14px 0;
    font-size: clamp(42px, 5vw, 68px);
    line-height: 1;
    letter-spacing: -2.5px;
  }

  .details-synopsis {
    color: #c6cbd4;
    line-height: 1.7;
    font-size: 16px;
    max-width: 680px;
  }

  .details-stats {
    display: flex;
    gap: 11px;
    flex-wrap: wrap;
    margin: 22px 0;
    color: #a4abb7;
    font-size: 13px;
    font-weight: 650;
  }

  .language-filter {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    color: #8c93a0;
    font-size: 13px;
  }

  .language-pill {
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    color: #cdd1d8;
    cursor: pointer;
    border: 1px solid transparent;
  }

  .language-pill:hover,
  .language-pill.active {
    background: rgba(255,138,91,0.15);
    border-color: rgba(255,138,91,0.45);
    color: #ffad91;
  }

  .details-main {
    width: min(1200px, calc(100% - 48px));
    margin: auto;
    padding: 55px 0 100px;
  }

  .episode-section {
    margin-bottom: 58px;
  }

  .episode-section-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 18px;
  }

  .eyebrow {
    color: #ff8962;
    font-size: 10px;
    font-weight: 850;
    letter-spacing: 1.6px;
  }

  .episode-section-heading h2 {
    margin: 5px 0 0;
    font-size: 28px;
    letter-spacing: -0.7px;
  }

  .episode-count {
    color: #727a88;
    font-size: 13px;
  }

  .episode-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .episode-card {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 12px;
    border-radius: 15px;
    border: 1px solid rgba(255,255,255,0.07);
    background: rgba(255,255,255,0.035);
    transition: 0.2s ease;
  }

  .episode-card:hover {
    background: rgba(255,255,255,0.06);
    border-color: rgba(255,255,255,0.12);
    transform: translateY(-1px);
  }

  .episode-number {
    width: 30px;
    text-align: center;
    color: #59606d;
    font-size: 12px;
    font-weight: 800;
  }

  .episode-thumb {
    position: relative;
    width: 190px;
    flex: 0 0 190px;
    aspect-ratio: 16 / 9;
    overflow: hidden;
    border-radius: 10px;
    background: #171a21;
  }

  .episode-thumb img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
  }

  .episode-thumb-placeholder {
    width: 100%;
    height: 100%;
    display: grid;
    place-items: center;
    background:
      radial-gradient(
        circle at 50% 40%,
        rgba(255,138,91,0.18),
        transparent 50%
      ),
      #171a21;
    color: #ff9b78;
    font-size: 24px;
  }

  .episode-thumb-placeholder.trailer {
    background:
      radial-gradient(
        circle at 50% 40%,
        rgba(100,170,255,0.18),
        transparent 50%
      ),
      #171a21;
  }

  .episode-play-overlay {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgba(0,0,0,0.2);
    opacity: 0;
    transition: 0.2s;
  }

  .episode-card:hover .episode-play-overlay {
    opacity: 1;
  }

  .episode-play-overlay span {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    padding-left: 2px;
    border-radius: 50%;
    background: rgba(255,255,255,0.92);
    color: #11141a;
  }

  .episode-info {
    flex: 1;
    min-width: 0;
  }

  .episode-info h3 {
    margin: 0 0 6px;
    font-size: 16px;
  }

  .episode-info p {
    margin: 0;
    color: #7e8693;
    font-size: 13px;
    line-height: 1.5;
    max-width: 620px;
  }

  .episode-meta {
    display: flex;
    gap: 12px;
    margin-top: 9px;
    color: #646c79;
    font-size: 11px;
  }

  .episode-actions {
    display: flex;
    gap: 7px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .play-language {
    padding: 8px 11px;
    border-radius: 8px;
    background: rgba(255,255,255,0.08);
    color: #e9ebef;
    cursor: pointer;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }

  .play-language:hover {
    background: #ff7454;
    color: white;
  }

  .trailer-section {
    margin-top: 30px;
    padding-top: 40px;
    border-top: 1px solid rgba(255,255,255,0.08);
  }

  .trailer-label {
    display: inline-block;
    margin-bottom: 7px;
    color: #ff956f;
    font-size: 9px;
    font-weight: 850;
    letter-spacing: 1.4px;
  }

  .details-back {
    display: flex;
    justify-content: center;
    padding-top: 25px;
  }

  /* FOOTER */

  .footer {
    border-top: 1px solid rgba(255,255,255,0.06);
    padding: 32px 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 9px;
    color: #5f6673;
    text-align: center;
  }

  .footer-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #aeb4bf;
    font-weight: 800;
  }

  .footer-brand .brand-mark {
    width: 26px;
    height: 26px;
    border-radius: 7px;
    font-size: 13px;
  }

  .footer p {
    margin: 0;
    font-size: 12px;
  }

  .footer-version {
    font-size: 10px;
    color: #464c57;
  }

  /* RESPONSIVE */

  @media (max-width: 1100px) {
    .show-row,
    .loading-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .hero {
      min-height: 520px;
    }
  }

  @media (max-width: 800px) {
    .navbar-inner,
    .hero-content,
    .main-content,
    .details-content,
    .details-main {
      width: min(100% - 30px, 1400px);
    }

    .navbar {
      height: auto;
      padding: 12px 0;
    }

    .navbar-inner {
      flex-direction: column;
      align-items: stretch;
      gap: 10px;
    }

    .brand {
      font-size: 19px;
    }

    .search-wrapper {
      width: 100%;
    }

    .hero {
      min-height: 560px;
    }

    .hero-content {
      padding-bottom: 55px;
    }

    .hero h1 {
      font-size: 46px;
      letter-spacing: -2px;
    }

    .show-row,
    .loading-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .details-content {
      align-items: flex-start;
      flex-direction: column;
      padding-top: 100px;
    }

    .details-poster-wrap {
      width: 170px;
      flex-basis: auto;
    }

    .episode-card {
      align-items: flex-start;
      flex-wrap: wrap;
    }

    .episode-number {
      display: none;
    }

    .episode-thumb {
      width: 150px;
      flex-basis: 150px;
    }

    .episode-info {
      min-width: calc(100% - 180px);
    }

    .episode-actions {
      width: 100%;
      justify-content: flex-start;
      padding-left: 168px;
    }
  }

  @media (max-width: 560px) {
    .main-content {
      padding-top: 20px;
    }

    .hero {
      min-height: 500px;
    }

    .hero-content {
      padding-bottom: 40px;
    }

    .hero h1 {
      font-size: 38px;
    }

    .hero p {
      font-size: 14px;
    }

    .hero-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .show-row,
    .loading-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 13px;
    }

    .content-section {
      margin-bottom: 38px;
    }

    .section-header h2 {
      font-size: 21px;
    }

    .details-info h1 {
      font-size: 42px;
    }

    .details-poster-wrap {
      width: 145px;
    }

    .episode-card {
      display: grid;
      grid-template-columns: 115px 1fr;
      gap: 12px;
    }

    .episode-thumb {
      width: 115px;
      flex-basis: auto;
      grid-row: span 2;
    }

    .episode-info {
      min-width: 0;
    }

    .episode-info p {
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .episode-actions {
      padding-left: 0;
      width: 100%;
      grid-column: 1 / -1;
    }

    .back-button {
      left: 15px;
      top: 15px;
    }
  }
`;
export default App;