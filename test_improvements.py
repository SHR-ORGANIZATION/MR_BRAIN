"""Test script for schedule/document improvements."""
import re
from pathlib import Path


def _safe_filename(name):
    safe = re.sub(r"['\u2018\u2019`]", '', name)
    safe = re.sub(r'[^\w\s-]', '', safe)
    safe = re.sub(r'\s+', '_', safe).strip('_')
    return safe[:60]


def test_command(cmd):
    cmd_lower = cmd.lower().strip()
    
    # Step 4: doc_type
    doc_type = None
    if re.search(r'\bschedule\b|\bschedules\b|\bplan\b|\bratiba\b', cmd_lower):
        doc_type = 'schedule'
    
    # Step 4b: topic from command itself
    topic = None
    if not topic and doc_type == 'schedule':
        schedule_topic_match = re.search(r'(?:create|make|generate|write)\s+([\w\s]+?)\s*(?:schedules?|schedule|plan|ratiba)', cmd_lower, re.I)
        if schedule_topic_match:
            topic = schedule_topic_match.group(1).strip()
            for filler in ['a', 'an', 'the', 'my', 'our']:
                topic = re.sub(r'\b' + filler + r'\b', '', topic, flags=re.I).strip()
            if topic:
                topic = topic.title()
        if not topic:
            topic = 'Training Schedule'
    
    # Step 3: topic from about/on/to learn
    topic_patterns = [
        r'(?:content\s+)?(?:about|on|regarding)\s+(.+?)(?:\s*$)',
        r'(?:write|generate|create|make)\s+(?:.+?)\s+(?:about|on|regarding)\s+(.+?)(?:\s*$)',
        r'(?:to learn|for learning|learn)\s+(.+?)(?:\s*$)',
    ]
    for pattern in topic_patterns:
        m = re.search(pattern, cmd_lower, re.I)
        if m:
            topic_from_about = m.group(1).strip()
            for stop_word in ['also', 'then', 'and', 'but', 'save', 'name']:
                topic_from_about = re.sub(r'\s+' + stop_word + r'\b.*$', '', topic_from_about, flags=re.I).strip()
            if topic_from_about:
                topic = topic_from_about
                break
    
    # Step 5: person name
    person_name = None
    if doc_type == 'schedule':
        name_match = re.search(r'(?:create|make|generate|write)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)\s+(?:schedule|plan|ratiba)', cmd_lower)
        if not name_match:
            name_match = re.search(r'(?:schedule|plan|ratiba|schedules)\s+(?:for|ya|wa|kwa)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)', cmd_lower)
        if not name_match:
            name_match = re.search(r'(?:nataka|taka)\s+(?:schedule|ratiba|schedules)\s+(?:ya|wa|kwa)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)', cmd_lower)
        if not name_match:
            name_match = re.search(r'(?:schedule|plan|schedules)\s+(?:for|ya|wa)\s+([a-z]+\s+[a-z]+)', cmd_lower, re.I)
        if not name_match:
            name_match = re.search(r'(?:schedule|plan|schedules)\s+(?:for|ya|wa)\s+([a-z]+)(?:\s|$|\.)', cmd_lower, re.I)
        if name_match:
            person_name = name_match.group(1).strip().title()
            if topic and ('to learn' in topic.lower() or 'about' in topic.lower() or person_name.lower() not in topic.lower()):
                topic = re.sub(r'to\s+learn\s+', '', topic, flags=re.I).strip()
                topic = re.sub(r'about\s+', '', topic, flags=re.I).strip()
                if person_name.lower() not in topic.lower():
                    topic = f"{person_name}'s {topic.title()}"
    
    # Step 5b
    if person_name:
        topic_match = re.search(r'(?:about|to learn|for learning|on)\s+(.+?)(?:\s*$)', cmd_lower, re.I)
        if topic_match:
            topic_text = topic_match.group(1).strip()
            topic_text = re.sub(r'^to\s+learn\s+', '', topic_text, flags=re.I).strip()
            for stop_word in ['also', 'then', 'and', 'but', 'save', 'name']:
                topic_text = re.sub(r'\s+' + stop_word + r'\b.*$', '', topic_text, flags=re.I).strip()
            if topic_text:
                topic = f"{person_name}'s {topic_text.title()} Training Schedule"
        else:
            _generic = {'work', 'training', 'professional', 'personal', 'daily', 'weekly'}
            current_base = topic.replace(f"{person_name}'s ", "").strip().lower() if topic else ""
            if current_base in _generic or not topic:
                base_topic = topic.replace(f"{person_name}'s ", "").strip() if topic else "Training"
                topic = f"{person_name}'s {base_topic.title()} Schedule"
            elif not topic.lower().endswith("schedule"):
                base_topic = topic.replace(f"{person_name}'s ", "").strip()
                topic = f"{person_name}'s {base_topic.title()} Schedule"
    
    # Step 6 fallback
    if not topic:
        topic = 'Training Schedule'
    
    # Step 7: output path
    safe_topic = _safe_filename(topic)
    if topic.lower().endswith('schedule'):
        output = f'{safe_topic}.docx'
    else:
        output = f'{safe_topic}_Schedule.docx'
    
    print(f'CMD: {cmd}')
    print(f'  doc_type={doc_type}, person={person_name}')
    print(f'  topic={topic}')
    print(f'  OUTPUT: {output}')
    print()


# Test cases
test_command('create professional training schedules!')
test_command('create professional training schedules for hamisi juma about to learn arabic')
test_command('make schedule for Leo')
test_command('create schedule for Shakira')
test_command('generate work schedule for john doe')
test_command('write arabic training schedule for fatma')
test_command('nataka schedule ya Ali')
