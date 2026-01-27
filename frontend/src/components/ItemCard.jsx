import React from 'react';

const ItemCard = ({ item }) => {
    return (
        <div className="glass-panel animate-fade-in" style={{ padding: '1.25rem', position: 'relative' }}>
            <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                marginBottom: '0.5rem',
                display: 'flex',
                justifyContent: 'space-between'
            }}>
                <span>{new Date(item.publication_date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
            </div>

            <h3 style={{ marginBottom: '0.75rem' }}>
                <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                        color: 'var(--text-primary)',
                        textDecoration: 'none',
                        transition: 'color 0.2s'
                    }}
                    onMouseOver={(e) => e.target.style.color = 'var(--accent-color)'}
                    onMouseOut={(e) => e.target.style.color = 'var(--text-primary)'}
                >
                    {item.title}
                </a>
            </h3>
            <p style={{
                color: 'var(--text-secondary)',
                fontSize: '0.95rem',
                marginBottom: '1rem',
                lineHeight: '1.5'
            }}>
                {item.description_fr || item.description}
            </p>

            {item.tags && item.tags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {item.tags.map(tag => (
                        <span key={tag} style={{
                            fontSize: '0.7rem',
                            color: 'var(--text-secondary)',
                            background: 'rgba(255, 255, 255, 0.05)',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '0.4rem',
                            border: '1px solid rgba(255, 255, 255, 0.1)'
                        }}>
                            #{tag}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ItemCard;
