import re

# Read the file
with open(r'c:\Users\Admin\AIX\localy\src\components\PersonalInfoEditScreen.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Change handleSearchAddress to use modal
content = content.replace(
    '''    // 우편번호 찾기 (Daum Postcode) - SignUpForm과 동일하게 사용
    const handleSearchAddress = () => {
        if (window.daum && window.daum.Postcode) {
            new window.daum.Postcode({
                oncomplete: function (data: any) {
                    setUserInfo(prev => ({
                        ...prev,
                        user_post: data.zonecode,
                        user_addr1: data.roadAddress
                    }));
                }
            }).open();
        } else {
            alert('우편번호 서비스를 불러오는 중입니다. 잠시 후 다시 시도해주세요.');
        }
    };''',
    '''    // 우편번호 찾기 - Modal 방식으로 변경
    const handleSearchAddress = () => {
        setIsAddressModalOpen(true);
    };''')

# Fix 2: Remove disabled from email input
content = content.replace(
    'disabled={isEmailVerified && !emailChanged}',
    '')

# Fix 3: Remove backgroundColor condition from email input
content = content.replace(
    "style={{ ...inputStyle, backgroundColor: (isEmailVerified && !emailChanged) ? '#f5f5f5' : 'white' }}",
    'style={inputStyle}')

# Write back
with open(r'c:\Users\Admin\AIX\localy\src\components\PersonalInfoEditScreen.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("File updated successfully!")
