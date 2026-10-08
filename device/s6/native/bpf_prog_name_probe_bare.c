/* Freestanding ephemeral program-name probe for Recovery without /system linker. */
#include <stdint.h>
static long call(long n,long a,long b,long c,long d){
 register long x0 __asm__("x0")=a;register long x1 __asm__("x1")=b;
 register long x2 __asm__("x2")=c;register long x3 __asm__("x3")=d;
 register long x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory");return x0;
}
static void print(const char*s){long z=0;while(s[z])z++;call(64,1,(long)s,z,0);}
static void number(long n){char b[24];unsigned i=0;if(n<0){print("-");n=-n;}do{b[i++]=(char)('0'+n%10);n/=10;}while(n);while(i)call(64,1,(long)&b[--i],1,0);}
void _start(void){
 char u[390];for(unsigned i=0;i<sizeof(u);i++)u[i]=0;
 if(call(160,(long)u,0,0,0)==0){print("kernel=");print(u+130);print("\n");}
 for(unsigned named=0;named<2;named++){
  uint32_t attr[38];for(unsigned i=0;i<38;i++)attr[i]=0;
  uint64_t insns[2]={0x00000000000000b7ULL,0x0000000000000095ULL};
  char license[]="GPL",log[4096];for(unsigned i=0;i<sizeof(log);i++)log[i]=0;
  attr[0]=1;attr[1]=2;
  ((uint64_t*)attr)[1]=(uint64_t)insns;((uint64_t*)attr)[2]=(uint64_t)license;
  attr[6]=1;attr[7]=sizeof(log);((uint64_t*)attr)[4]=(uint64_t)log;
  const char *s="t860_abi_probe";if(named)for(unsigned i=0;i<14;i++)((char*)attr)[48+i]=s[i];
  long fd=call(280,5,(long)attr,sizeof(attr),0);
  print(named?"prog_named=1 result=":"prog_named=0 result=");number(fd);
  print(" verifier=");print(log);print("\n");
  if(fd>=0)call(57,fd,0,0,0);
 }
 call(93,0,0,0,0);__builtin_unreachable();
}
