import React, { useState, useEffect, useRef } from 'react';
import ItemCard from './components/ItemCard';
import PromptCard from './components/PromptCard';
import Calendar from './components/Calendar';

function App() {
  const [items, setItems] = useState([]);
  const [dates, setDates] = useState([]);
  const [tags, setTags] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [tempTags, setTempTags] = useState([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);
  const [loading, setLoading] = useState(true);
  const hoverTimeoutRef = useRef(null);
  const calendarRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002';

  useEffect(() => {
    fetchDates();
    fetchTags();
  }, []);

  useEffect(() => {
    if (selectedDate || selectedTags.length > 0 || (dates.length > 0)) {
      fetchItems(selectedDate, selectedTags);
    }
  }, [selectedDate, selectedTags, dates]);

  const fetchDates = async () => {
    try {
      const response = await fetch(`${API_URL}/dates`);
      const data = await response.json();
      setDates(data);
      if (data.length > 0 && !selectedDate) {
        setSelectedDate(data[0]);
      }
    } catch (error) {
      console.error('Error fetching dates:', error);
    }
  };

  const fetchTags = async () => {
    try {
      const response = await fetch(`${API_URL}/tags`);
      const data = await response.json();
      setTags(data);
    } catch (error) {
      console.error('Error fetching tags:', error);
    }
  };

  const fetchItems = async (date, tagList) => {
    setLoading(true);
    try {
      let url = `${API_URL}/items?`;
      if (tagList && tagList.length > 0) {
        const tagParams = tagList.map(t => `tag=${encodeURIComponent(t)}`).join('&');
        url += tagParams;
      } else if (date) {
        url += `target_date=${date}`;
      }

      const response = await fetch(url);
      const data = await response.json();
      setItems(data);
    } catch (error) {
      console.error('Error fetching items:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTagInDrawer = (tag) => {
    setTempTags(prev => {
      if (prev.includes(tag)) {
        return prev.filter(t => t !== tag);
      }
      if (prev.length >= 3) return prev;
      return [...prev, tag];
    });
  };

  const validateTags = () => {
    setSelectedTags(tempTags);
    setIsDrawerOpen(false);
    if (tempTags.length > 0) {
      setSelectedDate('');
    }
  };

  const cancelTags = () => {
    setTempTags(selectedTags);
    setIsDrawerOpen(false);
  };

  const clearFilters = () => {
    setSelectedTags([]);
    setTempTags([]);
    if (dates.length > 0) {
      setSelectedDate(dates[0]);
    }
  };

  const handleDateSelect = (date) => {
    setSelectedDate(date);
    setShowCalendar(false);
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setSelectedTags([]);
    setTempTags([]);
  };

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setShowCalendar(true);
  };

  const handleMouseLeave = () => {
    hoverTimeoutRef.current = setTimeout(() => {
      setShowCalendar(false);
    }, 300); // 300ms delay to allow moving into popover
  };

  const groupedItems = items.reduce((acc, item) => {
    const category = item.category || 'Other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(item);
    return acc;
  }, {});

  const categoryOrder = [
    'Prompt of the Day',
    'Breaking News',
    'Coming in Hot',
    'Today’s Spotlight',
    'AI Finds',
    'Notable AIs',
    'Open Source Finds'
  ];

  const otherCategories = Object.keys(groupedItems).filter(cat => !categoryOrder.includes(cat));
  const finalCategoryOrder = [...categoryOrder, ...otherCategories];

  const formattedSelectedDate = selectedDate ? new Date(selectedDate).toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long'
  }) : 'Choisir une date';

  return (
    <div className="app-container">
      <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
        <h1 className="gradient-text" style={{ fontSize: '3.5rem', marginBottom: '0.5rem' }}>TAAFT</h1>
        <p style={{ color: 'var(--text-secondary)' }}>There's An AI For That - Curated Daily</p>
      </header>

      <section className="header-controls">
        <div
          className="date-trigger-container"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          style={{ position: 'relative' }}
        >
          <div
            className="date-trigger"
            onClick={() => setShowCalendar(!showCalendar)}
            style={{ visibility: selectedTags.length > 0 ? 'hidden' : 'visible' }}
          >
            <span>📅 {formattedSelectedDate}</span>
          </div>

          {showCalendar && selectedTags.length === 0 && (
            <div className="calendar-popover">
              <Calendar
                currentDate={selectedDate}
                availableDates={dates}
                onDateSelect={handleDateSelect}
              />
            </div>
          )}
        </div>

        <button
          className="tag-btn"
          style={{
            background: '#fb923c',
            color: 'white',
            borderColor: '#fb923c',
            padding: '0.8rem 3rem',
            fontSize: '1.1rem',
            fontWeight: '600',
            boxShadow: '0 8px 16px -4px rgba(251, 146, 60, 0.4)'
          }}
          onClick={() => {
            setTempTags(selectedTags);
            setIsDrawerOpen(true);
          }}
        >
          ALL
        </button>

        {selectedTags.length > 0 && (
          <div className="active-tags-display" style={{ marginLeft: '1rem' }}>
            {selectedTags.map(tag => (
              <span key={tag} style={{
                color: '#fb923c',
                fontWeight: '600',
                background: 'rgba(251, 146, 60, 0.1)',
                padding: '0.5rem 1rem',
                borderRadius: '0.5rem',
                border: '1px solid rgba(251, 146, 60, 0.2)'
              }}>
                #{tag}
              </span>
            ))}
            <button className="btn-clear" onClick={clearFilters}>Retour Newsletter</button>
          </div>
        )}
      </section>

      {isDrawerOpen && (
        <div className="drawer-overlay" onClick={cancelTags}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h2 className="gradient-text">Select Tags (Max 3)</h2>
              <div className="tag-drawer-actions">
                <button
                  className="btn-validate"
                  onClick={validateTags}
                  style={{ opacity: tempTags.length > 0 ? 1 : 0.5 }}
                >
                  VALIDER
                </button>
                <button
                  className="btn-annuler"
                  onClick={cancelTags}
                >
                  ANNULER
                </button>
              </div>
            </div>

            <div className="drawer-tag-grid">
              {tags.map(tag => (
                <button
                  key={tag}
                  className={`tag-btn-lg ${tempTags.includes(tag) ? 'active' : ''}`}
                  onClick={() => toggleTagInDrawer(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', marginTop: '4rem' }}>
          <div className="gradient-text" style={{ fontSize: '1.5rem', fontWeight: '600' }}>Chargement...</div>
        </div>
      ) : (
        <div>
          {finalCategoryOrder.map(category => {
            const categoryItems = groupedItems[category];
            if (!categoryItems) return null;

            return (
              <section key={category} style={{ marginBottom: '5rem' }}>
                <h2 className="section-title">
                  {category}
                </h2>
                <div className="grid">
                  {categoryItems.map(item => (
                    category === 'Prompt of the Day' ?
                      <PromptCard key={item.id} item={item} /> :
                      <ItemCard key={item.id} item={item} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {items.length === 0 && !loading && (
        <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-secondary)' }}>
          Pas d'objets trouvés pour cette sélection.
        </div>
      )}

      <footer style={{ marginTop: '6rem', padding: '2rem', textAlign: 'center', borderTop: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        TAAFT Dashboard &copy; {new Date().getFullYear()} - Datligent Intelligence
      </footer>
    </div>
  );
}

export default App;
