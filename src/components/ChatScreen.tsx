import { motion } from 'motion/react';
import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import catImage from '../assets/cat.jpg';

interface ChatScreenProps {
    userName: string;
    onComplete: () => void;
}

interface Message {
    id: number;
    text: string;
    sender: 'user' | 'cat';
    timestamp: Date;
}

type QuestionStep = 'food' | 'location' | 'complete';

export function ChatScreen({ userName, onComplete }: ChatScreenProps) {
    // 동적 URL 설정 (다른 컴포넌트와 일관성 유지)
    const myUrl = window.location.protocol + "//" + window.location.hostname + ":8000";

    const [currentStep, setCurrentStep] = useState<QuestionStep>('food');
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 1,
            text: `안녕하세요, ${userName} 님! 🐱\n저는 여행 도우미 냥이에요!`,
            sender: 'cat',
            timestamp: new Date()
        },
        {
            id: 2,
            text: '혹시 내가 참고할만한 못먹는 음식같은게 있을까?',
            sender: 'cat',
            timestamp: new Date()
        }
    ]);
    const [inputText, setInputText] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // [수정] 답변을 로컬스토리지와 서버(DB)에 동시 저장
    const saveAnswerToPersona = async (step: QuestionStep, answer: string) => {
        try {
            // 1. 로컬스토리지에서 유저 정보 가져오기
            const userStr = localStorage.getItem('user');
            if (!userStr) return;

            let user = JSON.parse(userStr);
            const userId = user.user_id; // 아이디 확보

            // 2. 서버로 보낼 데이터 준비 (내 아이디 + 답변)
            let updateData: any = { user_id: userId };

            if (step === 'food') {
                user.non_preferred_food = answer;       // 화면용 업데이트
                updateData.non_preferred_food = answer; // 서버용 데이터 담기
            } else if (step === 'location') {
                user.non_preferred_region = answer;       // 화면용 업데이트
                updateData.non_preferred_region = answer; // 서버용 데이터 담기
            }

            // 3. 로컬스토리지 즉시 저장 (화면 반영)
            localStorage.setItem('user', JSON.stringify(user));
            console.log(`[Local] Saved ${step}:`, answer);

            // 4. [핵심] 서버로 전송해서 DB에 영구 저장!
            try {
                await fetch(`${myUrl}/auth/update-profile`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateData)
                });
                console.log(`[Server] Saved ${step} to DB`);
            } catch (serverError) {
                console.error('서버 저장 실패 (백엔드가 켜져있는지 확인하세요):', serverError);
            }

        } catch (e) {
            console.error('Error saving persona data:', e);
        }
    };

    const handleSend = () => {
        if (!inputText.trim()) return;

        // 1. 유저 메시지 화면에 표시
        const userMessage: Message = {
            id: messages.length + 1,
            text: inputText,
            sender: 'user',
            timestamp: new Date()
        };

        setMessages([...messages, userMessage]);

        // [중요] 2. 입력한 내용 저장 (현재 단계에 맞춰서!)
        saveAnswerToPersona(currentStep, inputText);

        setInputText('');

        // Handle cat response based on current step
        setTimeout(() => {
            let catResponse = '';
            let nextStep: QuestionStep = currentStep;

            if (currentStep === 'food') {
                catResponse = '알겠어요! 참고할게요 😺\n그럼 다음 질문이에요~';
                nextStep = 'location';
            } else if (currentStep === 'location') {
                catResponse = '좋아요! 모든 정보를 잘 기록했어요! ✨\n회원가입이 완료되었습니다!';
                nextStep = 'complete';
            }

            const catMessage: Message = {
                id: messages.length + 2,
                text: catResponse,
                sender: 'cat',
                timestamp: new Date()
            };

            setMessages(prev => [...prev, catMessage]);
            setCurrentStep(nextStep);

            // Add next question or complete
            if (nextStep === 'location') {
                setTimeout(() => {
                    const questionMessage: Message = {
                        id: messages.length + 3,
                        text: '혹시 피하고 싶은 여행지가 있을까?',
                        sender: 'cat',
                        timestamp: new Date()
                    };
                    setMessages(prev => [...prev, questionMessage]);
                }, 1000);
            } else if (nextStep === 'complete') {
                setTimeout(() => {
                    onComplete();
                }, 2000);
            }
        }, 1000);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            style={{
                width: '100%',
                height: '100vh',
                background: 'linear-gradient(135deg, #fef9e7 0%, #f9e79f 100%)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}
        >
            {/* Cat Image Section */}
            <motion.div
                initial={{ y: -30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6 }}
                style={{
                    padding: '0',
                    textAlign: 'center',
                    background: 'transparent'
                }}
            >
                <motion.img
                    src={catImage}
                    alt="Chat Cat"
                    animate={{
                        y: [0, -5, 0],
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                    style={{
                        width: '100%',
                        height: '280px',
                        objectFit: 'cover',
                        objectPosition: 'center',
                        display: 'block'
                    }}
                />
            </motion.div>

            {/* Chat Messages Section */}
            <div
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                    background: 'rgba(255, 255, 255, 0.5)',
                    borderTopLeftRadius: '30px',
                    borderTopRightRadius: '30px'
                }}
            >
                {messages.map((message) => (
                    <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                        style={{
                            display: 'flex',
                            justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
                            padding: '0 8px'
                        }}
                    >
                        <div
                            style={{
                                maxWidth: '70%',
                                padding: '12px 16px',
                                borderRadius: message.sender === 'user'
                                    ? '18px 18px 4px 18px'
                                    : '18px 18px 18px 4px',
                                background: message.sender === 'user'
                                    ? 'linear-gradient(135deg, #2D8B5F 0%, #3BA474 100%)'
                                    : '#fff',
                                color: message.sender === 'user' ? '#fff' : '#333',
                                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                                fontSize: '14px',
                                lineHeight: '1.6',
                                whiteSpace: 'pre-line'
                            }}
                        >
                            {message.text}
                        </div>
                    </motion.div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Section */}
            {currentStep !== 'complete' && (
                <motion.div
                    initial={{ y: 50, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                    style={{
                        padding: '16px 20px 20px',
                        background: '#fff',
                        borderTop: '2px solid rgba(243, 156, 18, 0.2)',
                        boxShadow: '0 -4px 12px rgba(0, 0, 0, 0.05)'
                    }}
                >
                    <div style={{
                        display: 'flex',
                        gap: '12px',
                        alignItems: 'flex-end',
                        maxWidth: '800px',
                        margin: '0 auto'
                    }}>
                        <input
                            type="text"
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="메시지를 입력하세요..."
                            style={{
                                flex: 1,
                                padding: '12px 16px',
                                borderRadius: '24px',
                                border: '2px solid rgba(243, 156, 18, 0.3)',
                                fontSize: '14px',
                                outline: 'none',
                                transition: 'all 0.2s',
                                background: '#fef9e7'
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#f39c12'}
                            onBlur={(e) => e.target.style.borderColor = 'rgba(243, 156, 18, 0.3)'}
                        />
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={handleSend}
                            disabled={!inputText.trim()}
                            style={{
                                width: '48px',
                                height: '48px',
                                borderRadius: '50%',
                                border: 'none',
                                background: inputText.trim()
                                    ? 'linear-gradient(135deg, #f39c12 0%, #e67e22 100%)'
                                    : '#ddd',
                                color: '#fff',
                                cursor: inputText.trim() ? 'pointer' : 'not-allowed',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                boxShadow: inputText.trim() ? '0 4px 12px rgba(243, 156, 18, 0.3)' : 'none',
                                transition: 'all 0.2s'
                            }}
                        >
                            <Send size={20} />
                        </motion.button>
                    </div>
                </motion.div>
            )}
        </motion.div>
    );
}