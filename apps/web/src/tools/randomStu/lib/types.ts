export type Student = {
  id: string;
  number: string;
  name: string;
  enabled: boolean;
};

export type Classroom = {
  id: string;
  name: string;
  students: Student[];
  locked: boolean;
  createdAt: string;
  updatedAt: string;
};

export type RandomStuData = {
  version: 1;
  classrooms: Classroom[];
  activeClassroomId: string | null;
};
