export const SAMPLE_VALID_SMALL = `# Small valid program: 1 exam with fixed slot
room hall_a capacity 100;
invigilator prof_x;
group cse_a size 80;

exam CS101
  room hall_a
  invigilator prof_x
  students cse_a
  slot 1;
`;

export const SAMPLE_VALID_AUTO = `# Automatic slot assignment (slot 0 = AUTO)
# The compiler will find a conflict-free slot via backtracking
room hall_a capacity 100;
room hall_b capacity 80;

invigilator prof_x;
invigilator prof_y;

group cse_a size 70;
group cse_b size 60;

exam CS101 room hall_a invigilator prof_x students cse_a slot 0;
exam CS102 room hall_a invigilator prof_x students cse_b slot 0;
exam CS201 room hall_b invigilator prof_y students cse_a slot 0;
`;

export const SAMPLE_VALID_LARGE = `# Multi-department exam timetable with 7 exams
room hall_a capacity 100;
room hall_b capacity 80;
room hall_c capacity 60;
room hall_d capacity 120;

invigilator prof_x;
invigilator prof_y;
invigilator prof_z;
invigilator prof_w;

group cse_a size 75;
group cse_b size 60;
group ece_a size 60;
group ece_b size 50;
group mech_a size 90;

exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
exam CS102 room hall_a invigilator prof_x students cse_a slot 2;
exam CS201 room hall_b invigilator prof_y students cse_b slot 1;
exam EC101 room hall_c invigilator prof_z students ece_a slot 1;
exam EC201 room hall_c invigilator prof_z students ece_b slot 2;
exam ME101 room hall_d invigilator prof_w students mech_a slot 1;
exam ME201 room hall_d invigilator prof_w students mech_a slot 2;
`;

export const SAMPLE_SEMANTIC_CAPACITY_ERROR = `# Semantic Error: Room capacity violation
# hall_a has capacity 50, but cse_a has 80 students
room hall_a capacity 50;
invigilator prof_x;
group cse_a size 80;

exam CS101
  room hall_a
  invigilator prof_x
  students cse_a
  slot 1;
`;

export const SAMPLE_SEMANTIC_CONFLICT_ERROR = `# Semantic Error: Room double-booking in Slot 1
room hall_a capacity 100;
invigilator prof_x;
invigilator prof_y;
group cse_a size 40;
group cse_b size 40;

exam CS101 room hall_a invigilator prof_x students cse_a slot 1;
exam CS102 room hall_a invigilator prof_y students cse_b slot 1;
`;

export const SAMPLE_SYNTAX_ERROR = `# Syntax Error: Missing semicolon
room hall_a capacity 100
invigilator prof_x;
`;

export const SAMPLE_LEXICAL_ERROR = `# Lexical Error: Invalid character '@'
room hall_a capacity @100;
`;
