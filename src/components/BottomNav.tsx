import React, { useState } from 'react';
import { Home, Bell, User, Settings, Plus, Sparkles, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface BottomNavProps {
    activeTab: string;
    onHomeClick: () => void;
    onNotificationClick: () => void;
    onAIScheduleClick: () => void;
    onManualScheduleClick: () => void;
    onMyPageClick: () => void; // 마이페이지
    onSettingsClick?: () => void; // 설정
}

export function BottomNav({
    activeTab,
    onHomeClick,
    onNotificationClick,
    onAIScheduleClick,
    onManualScheduleClick,
    onMyPageClick,
    onSettingsClick
}: BottomNavProps) {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    return (
        <>
            {/* 하단 네비게이션 바 (글래스모피즘) */}
            <div
                style={{
                    position: 'fixed',
                    bottom: 0,
                    left: '49.65%',
                    transform: 'translateX(-50%)',
                    width: '100%',
                    maxWidth: '480px',
                    height: '80px',
                    backgroundColor: 'rgba(255, 255, 255, 0.5)', // 반투명 흰색
                    backdropFilter: 'blur(24px)', // 강력한 블러
                    WebkitBackdropFilter: 'blur(24px)', // Safari 지원
                    borderTopLeftRadius: '24px',
                    borderTopRightRadius: '24px',
                    border: '1px solid rgba(255, 255, 255, 0.4)', // 은은한 테두리
                    borderBottom: 'none',
                    boxShadow: '0 -8px 32px rgba(0, 0, 0, 0.08)', // 부드러운 그림자
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0 30px',
                    zIndex: 50
                }}
            >
                {/* 왼쪽 메뉴 */}
                <div className="flex gap-4 items-center">
                    <NavIcon icon={<Home size={24} />} label="홈" isActive={activeTab === 'home'} onClick={onHomeClick} />
                    <NavIcon icon={<Bell size={24} />} label="알림" isActive={activeTab === 'notification'} onClick={onNotificationClick} />
                </div>

                {/* [수정] 중앙 공백 대폭 확대 (w-12 -> w-28) */}
                <div className="w-12" />

                {/* 오른쪽 메뉴 */}
                <div className="flex gap-4 items-center">
                    <NavIcon icon={<User size={24} />} label="MY" isActive={activeTab === 'mypage'} onClick={onMyPageClick} />
                    <NavIcon icon={<Settings size={24} />} label="설정" isActive={activeTab === 'settings'} onClick={onSettingsClick} />
                </div>
            </div>

            {/* 중앙 (+) 플로팅 버튼 및 메뉴 (화면 전체 기준 정렬) */}
            <div
                style={{
                    position: 'fixed',
                    bottom: '30px', // 바닥에서 약간 더 띄움
                    left: '49.65%',
                    transform: 'translateX(-50%)', // 절대 중앙 정렬
                    zIndex: 100,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '14px'
                }}
            >
                {/* 펼쳐지는 메뉴 아이템들 (글래스모피즘) */}
                <AnimatePresence>
                    {isMenuOpen && (
                        <>
                            {/* 1. 직접 일정 추가 */}
                            <motion.button
                                initial={{ y: 20, opacity: 0, scale: 0.8 }}
                                animate={{ y: 0, opacity: 1, scale: 1 }}
                                exit={{ y: 20, opacity: 0, scale: 0.8 }}
                                transition={{ duration: 0.2 }}
                                onClick={() => { setIsMenuOpen(false); onManualScheduleClick(); }}
                                style={{
                                    backgroundColor: 'rgba(255, 255, 255, 0.65)',
                                    backdropFilter: 'blur(20px)',
                                    WebkitBackdropFilter: 'blur(20px)',
                                    border: '1px solid rgba(255, 255, 255, 0.5)',
                                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
                                    borderRadius: '50px',
                                    padding: '12px 20px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    cursor: 'pointer'
                                }}
                            >
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center">
                                    <Calendar size={16} className="text-blue-600" />
                                </div>
                                <span className="text-sm font-bold text-gray-700 whitespace-nowrap">직접 일정 추가</span>
                            </motion.button>

                            {/* 2. AI와 일정 짜기 */}
                            <motion.button
                                initial={{ y: 20, opacity: 0, scale: 0.8 }}
                                animate={{ y: 0, opacity: 1, scale: 1 }}
                                exit={{ y: 20, opacity: 0, scale: 0.8 }}
                                transition={{ duration: 0.2, delay: 0.05 }}
                                onClick={() => { setIsMenuOpen(false); onAIScheduleClick(); }}
                                style={{
                                    backgroundColor: 'rgba(255, 255, 255, 0.65)',
                                    backdropFilter: 'blur(20px)',
                                    WebkitBackdropFilter: 'blur(20px)',
                                    border: '1px solid rgba(255, 255, 255, 0.5)',
                                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
                                    borderRadius: '50px',
                                    padding: '12px 20px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    cursor: 'pointer'
                                }}
                            >
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-100 to-yellow-200 flex items-center justify-center">
                                    <Sparkles size={16} className="text-yellow-600" />
                                </div>
                                <span className="text-sm font-bold text-gray-700 whitespace-nowrap">AI와 일정 짜기</span>
                            </motion.button>
                        </>
                    )}
                </AnimatePresence>

                {/* 메인 (+) 버튼 */}
                <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    animate={{ rotate: isMenuOpen ? 45 : 0 }}
                    style={{
                        width: '72px', // 버튼 크기 살짝 키움 (64 -> 72)
                        height: '72px',
                        borderRadius: '50%',
                        backgroundColor: '#89C765',
                        border: '5px solid #F9FCF5', // 배경색과 같은 테두리로 구멍 뚫린 느낌
                        boxShadow: '0 8px 20px rgba(137, 199, 101, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        color: 'white'
                    }}
                >
                    <Plus size={36} strokeWidth={2.5} />
                </motion.button>
            </div>
        </>
    );
}

// 네비게이션 아이콘 컴포넌트
function NavIcon({ icon, label, isActive, onClick }: any) {
    return (
        <div onClick={onClick} className="flex flex-col items-center cursor-pointer gap-1.5 w-12">
            <div className={`transition-colors duration-200 ${isActive ? 'text-[#89C765]' : 'text-gray-400'}`}>
                {icon}
            </div>
            <span className={`text-[11px] font-medium ${isActive ? 'text-[#89C765]' : 'text-gray-400'}`}>
                {label}
            </span>
        </div>
    );
}