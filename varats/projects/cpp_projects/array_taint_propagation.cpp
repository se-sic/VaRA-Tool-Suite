int main() {

  ___REGION_START __RT_Commit "Initialize"
  char *strings[1024];
  strings[42] = getenv("gude");
  ___REGION_END __RT_Commit "Initialize"

  ___REGION_START __RT_Commit "Assignment"
  char **strings_ptr = strings;
  char *t1 = strings_ptr[42];
  ___REGION_END __RT_Commit "Assignment"

  return 0;
}