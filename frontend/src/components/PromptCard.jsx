import React from 'react';

const PromptCard = ({ item }) => {
    return (
        <div className="glass-panel animate-fade-in" style={{
            gridColumn: '1 / -1',
            border: '2px solid rgba(168, 85, 247, 0.4)',
            background: 'linear-gradient(135deg, rgba(23, 23, 33, 0.8) 0%, rgba(45, 21, 60, 0.4) 100%)',
            padding: '2rem'
        }}>
            <div style={{
                fontSize: '0.85rem',
                color: 'rgba(255, 255, 255, 0.6)',
                marginBottom: '1rem',
                display: 'flex',
                justifyContent: 'space-between'
            }}>
                <span>{new Date(item.publication_date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
                <span style={{ color: '#a855f7', fontWeight: 'bold' }}>PROMPT OF THE DAY</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h2 style={{ fontSize: '2.5rem', marginBottom: '1.5rem' }}>
                        <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'white', textDecoration: 'none' }}
                            onMouseOver={(e) => e.target.style.color = '#a855f7'}
                            onMouseOut={(e) => e.target.style.color = 'white'}
                        >
                            {item.title}
                        </a>
                    </h2>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '3rem' }}>⚡</span>
                </div>
            </div>

            <div style={{
                background: 'rgba(0, 0, 0, 0.3)',
                padding: '1.5rem',
                borderRadius: '1rem',
                borderLeft: '4px solid #a855f7',
                marginBottom: '1.5rem'
            }}>
                <p style={{ color: 'var(--text-primary)', fontStyle: 'italic', fontSize: '1.2rem', lineHeight: '1.6' }}>
                    {item.description_fr || item.description}
                </p>
            </div>

            {item.tags && item.tags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                    {item.tags.map(tag => (
                        <span key={tag} style={{
                            fontSize: '0.8rem',
                            color: 'var(--text-primary)',
                            background: 'rgba(168, 85, 247, 0.2)',
                            padding: '0.25rem 0.75rem',
                            borderRadius: '0.5rem',
                            border: '1px solid rgba(168, 85, 247, 0.4)'
                        }}>
                            #{tag}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default PromptCard;
