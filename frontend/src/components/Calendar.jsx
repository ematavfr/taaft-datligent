import React, { useState } from 'react';

const Calendar = ({ currentDate, availableDates, onDateSelect }) => {
    const [viewDate, setViewDate] = useState(new Date(currentDate || new Date()));

    // Get days in month
    const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
    const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

    const daysInMonth = getDaysInMonth(viewDate.getFullYear(), viewDate.getMonth());
    const firstDay = getFirstDayOfMonth(viewDate.getFullYear(), viewDate.getMonth());

    const monthNames = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ];

    const changeMonth = (offset) => {
        setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + offset, 1));
    };

    const changeYear = (offset) => {
        setViewDate(new Date(viewDate.getFullYear() + offset, viewDate.getMonth(), 1));
    };

    const isSelected = (day) => {
        if (!currentDate) return false;
        const d = new Date(currentDate);
        return d.getDate() === day &&
            d.getMonth() === viewDate.getMonth() &&
            d.getFullYear() === viewDate.getFullYear();
    };

    const isAvailable = (day) => {
        const dateStr = `${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        return availableDates.includes(dateStr);
    };

    const handleDateClick = (day) => {
        if (isAvailable(day)) {
            const selected = `${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            onDateSelect(selected);
        }
    };

    const days = [];
    // Correcting for Monday start if desired, or just standard 0=Sunday
    // For standard: 0=Sun, 1=Mon...
    for (let i = 0; i < firstDay; i++) {
        days.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const available = isAvailable(d);
        const selected = isSelected(d);
        days.push(
            <div
                key={d}
                className={`calendar-day ${available ? 'available' : ''} ${selected ? 'selected' : ''}`}
                onClick={() => handleDateClick(d)}
            >
                {d}
            </div>
        );
    }

    return (
        <div className="calendar-container glass-panel">
            <div className="calendar-header">
                <div className="calendar-nav">
                    <button onClick={() => changeYear(-1)} className="nav-btn">«</button>
                    <button onClick={() => changeMonth(-1)} className="nav-btn">‹</button>
                </div>
                <div className="calendar-title">
                    {monthNames[viewDate.getMonth()]} {viewDate.getFullYear()}
                </div>
                <div className="calendar-nav">
                    <button onClick={() => changeMonth(1)} className="nav-btn">›</button>
                    <button onClick={() => changeYear(1)} className="nav-btn">»</button>
                </div>
            </div>
            <div className="calendar-weekdays">
                <div>Dim</div><div>Lun</div><div>Mar</div><div>Mer</div><div>Jeu</div><div>Ven</div><div>Sam</div>
            </div>
            <div className="calendar-grid">
                {days}
            </div>
        </div>
    );
};

export default Calendar;
