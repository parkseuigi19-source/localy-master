# Read file
with open(r'c:\Users\Admin\AIX\localy\src\components\PersonalInfoEditScreen.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: Change handleSearchAddress (lines 272-286)
# Find the line with "const handleSearchAddress"
in_handle_search = False
for i in range(len(lines)):
    if 'const handleSearchAddress = () =>' in lines[i]:
        in_handle_search = True
        handle_search_start = i
    if in_handle_search and '}).open();' in lines[i]:
        # Replace from start to this line
        lines[handle_search_start:i+1] = [
            '    // 우편번호 찾기 - Modal 방식으로 변경\n',
            '    const handleSearchAddress = () => {\n',
            '        setIsAddressModalOpen(true);\n'
        ]
        # Find and remove the else block
        j = i + 1
        while j < len(lines) and '    };' not in lines[j]:
            j += 1
        if '    };' in lines[j]:
            lines[i+1:j+1] = ['    };\n']
        in_handle_search = False
        break

# Fix 2 & 3: Remove disabled and backgroundColor from email input (around line 458-459)
for i in range(len(lines)):
    if 'disabled={isEmailVerified && !emailChanged}' in lines[i]:
        lines[i] = ''
    if 'backgroundColor: (isEmailVerified && !emailChanged)' in lines[i]:
        lines[i] = lines[i].replace(', backgroundColor: (isEmailVerified && !emailChanged) ? \'#f5f5f5\' : \'white\'', '')

# Write back
with open(r'c:\Users\Admin\AIX\localy\src\components\PersonalInfoEditScreen.tsx', 'w', encoding='utf-8') as f:
    f.writelines([line for line in lines if line.strip() or line == '\n'])

print("Fixed successfully!")
