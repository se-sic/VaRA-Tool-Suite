#include <stdlib.h>

int main() {

  ___REGION_START __RT_Commit "Initialize"
  int rc;
  char *t = getenv("gude");
  ___REGION_END __RT_Commit "Initialize"


  ___REGION_START __RT_Commit "Calculation"
  if (t != NULL) {
    ___REGION_START __RT_Commit "Then"
    rc = 4711;
    ___REGION_END __RT_Commit "Then"
  } else {
    ___REGION_START __RT_Commit "Else"
    rc = 42;
    ___REGION_END __RT_Commit "Else"
  }
  ___REGION_END __RT_Commit "Calculation"
  ___REGION_START __RT_Commit "Return"
  return rc;
  ___REGION_END __RT_Commit "Return"
}