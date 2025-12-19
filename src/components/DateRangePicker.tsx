import { useState } from 'react';
import { motion } from 'motion/react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface DateRangePickerProps {
    startDate: string;
    endDate: string;
    onDateSelect: (startDate: string, endDate: string) => void;
    minDate?: string;
}

export function DateRangePicker({ startDate, endDate, onDateSelect, minDate }: DateRangePickerProps) {
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [selectingStart, setSelectingStart] = useState(true);
    const [tempStartDate, setTempStartDate] = useState(startDate);
    const [tempEndDate, setTempEndDate] = useState(endDate);

    // Parse minDate correctly in local timezone
    let today: Date;
    if (minDate) {
        const [year, month, day] = minDate.split('-').map(Number);
        today = new Date(year, month - 1, day);
    } else {
        today = new Date();
    }
    today.setHours(0, 0, 0, 0);

    const getDaysInMonth = (date: Date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();

        return { daysInMonth, startingDayOfWeek, year, month };
    };

    const { daysInMonth, startingDayOfWeek, year, month } = getDaysInMonth(currentMonth);

    const handleDateClick = (day: number) => {
        const selectedDate = new Date(year, month, day);
        selectedDate.setHours(0, 0, 0, 0);

        // Check if date is in the past
        if (selectedDate < today) return;

        // Format date as YYYY-MM-DD in local timezone
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

        if (selectingStart) {
            setTempStartDate(dateStr);
            setTempEndDate('');
            setSelectingStart(false);
        } else {
            // If selected date is before start date, swap them
            if (dateStr < tempStartDate) {
                setTempEndDate(tempStartDate);
                setTempStartDate(dateStr);
                onDateSelect(dateStr, tempStartDate);
            } else {
                setTempEndDate(dateStr);
                onDateSelect(tempStartDate, dateStr);
            }
            setSelectingStart(true);
        }
    };

    const isDateInRange = (day: number) => {
        if (!tempStartDate || !tempEndDate) return false;
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        return dateStr >= tempStartDate && dateStr <= tempEndDate;
    };

    const isStartDate = (day: number) => {
        if (!tempStartDate) return false;
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        return dateStr === tempStartDate;
    };

    const isEndDate = (day: number) => {
        if (!tempEndDate) return false;
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        return dateStr === tempEndDate;
    };

    const isPastDate = (day: number) => {
        const date = new Date(year, month, day);
        date.setHours(0, 0, 0, 0);
        return date < today;
    };

    const changeMonth = (delta: number) => {
        setCurrentMonth(new Date(year, month + delta, 1));
    };

    const monthNames = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];
    const dayNames = ['일', '월', '화', '수', '목', '금', '토'];

    return (
        <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '12px',  // Reduced from 16px
            border: '1px solid #DEE2E6'
        }}>
            {/* Month Navigation */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px'  // Reduced from 12px
            }}>
                <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => changeMonth(-1)}
                    style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        border: '1px solid #DEE2E6',
                        background: 'white',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                >
                    <ChevronLeft size={16} color="#495057" />
                </motion.button>

                <span style={{
                    fontSize: '15px',
                    fontWeight: '700',
                    color: '#2D8B5F'
                }}>
                    {year}년 {monthNames[month]}
                </span>

                <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => changeMonth(1)}
                    style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        border: '1px solid #DEE2E6',
                        background: 'white',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                >
                    <ChevronRight size={16} color="#495057" />
                </motion.button>
            </div>

            {/* Day Names */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: '2px',
                marginBottom: '2px'  // Reduced from 4px
            }}>
                {dayNames.map((day) => (
                    <div key={day} style={{
                        textAlign: 'center',
                        fontSize: '11px',
                        fontWeight: '600',
                        color: '#868E96',
                        padding: '4px 0'
                    }}>
                        {day}
                    </div>
                ))}
            </div>

            {/* Calendar Days */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: '2px'
            }}>
                {/* Empty cells for days before month starts */}
                {Array.from({ length: startingDayOfWeek }).map((_, i) => (
                    <div key={`empty-${i}`} />
                ))}

                {/* Days of the month */}
                {Array.from({ length: daysInMonth }).map((_, i) => {
                    const day = i + 1;
                    const isInRange = isDateInRange(day);
                    const isStart = isStartDate(day);
                    const isEnd = isEndDate(day);
                    const isPast = isPastDate(day);

                    return (
                        <motion.button
                            key={day}
                            onClick={() => handleDateClick(day)}
                            disabled={isPast}
                            style={{
                                padding: '6px 4px',  // Reduced from 8px 4px
                                borderRadius: '50%',
                                border: 'none',
                                background: isStart || isEnd
                                    ? '#2D8B5F'
                                    : isInRange
                                        ? '#E8F5E9'
                                        : 'transparent',
                                color: isStart || isEnd
                                    ? 'white'
                                    : isPast
                                        ? '#CED4DA'
                                        : '#495057',
                                fontSize: '13px',
                                fontWeight: isStart || isEnd ? '700' : '500',
                                cursor: isPast ? 'not-allowed' : 'pointer',
                                transition: 'all 0.2s',
                                aspectRatio: '1',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            {day}
                        </motion.button>
                    );
                })}
            </div>

            {/* Selected Date Display */}
            {tempStartDate && (
                <div style={{
                    marginTop: '12px',
                    padding: '10px',
                    backgroundColor: '#F8F9FA',
                    borderRadius: '10px',
                    fontSize: '12px',
                    color: '#495057',
                    textAlign: 'center'
                }}>
                    {tempEndDate ? (
                        <span>
                            <strong>{tempStartDate}</strong> ~ <strong>{tempEndDate}</strong>
                        </span>
                    ) : (
                        <span>
                            시작일: <strong>{tempStartDate}</strong> (종료일을 선택하세요)
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}
