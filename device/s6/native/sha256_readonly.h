/* SHA256 read-only implementation shared from the existing reviewed guard. */
struct digest { uint32_t s[8]; uint64_t bytes; size_t used; unsigned char block[64]; };
static uint32_t rotr(uint32_t v, unsigned n) { return (v >> n) | (v << (32 - n)); }
static void transform(struct digest *d, const unsigned char *p) {
    static const uint32_t k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32_t w[64];
    for (size_t i=0; i<16; i++) w[i]=((uint32_t)p[i*4]<<24)|((uint32_t)p[i*4+1]<<16)|((uint32_t)p[i*4+2]<<8)|p[i*4+3];
    for (size_t i=16; i<64; i++) w[i]=w[i-16]+(rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10));
    uint32_t a=d->s[0],b=d->s[1],c=d->s[2],e=d->s[4],f=d->s[5],g=d->s[6],h=d->s[7],v=d->s[3];
    for (size_t i=0; i<64; i++) {
        uint32_t t=h+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^((~e)&g))+k[i]+w[i];
        uint32_t u=(rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=v+t;v=c;c=b;b=a;a=t+u;
    }
    d->s[0]+=a;d->s[1]+=b;d->s[2]+=c;d->s[3]+=v;d->s[4]+=e;d->s[5]+=f;d->s[6]+=g;d->s[7]+=h;
}
static void update(struct digest *d, const unsigned char *p, size_t n) {
    d->bytes+=n;
    while (n) {
        size_t z=64-d->used;if(z>n)z=n;
        memcpy(d->block+d->used,p,z);d->used+=z;p+=z;n-=z;
        if(d->used==64){transform(d,d->block);d->used=0;}
    }
}
static int hash_fd(int fd, char hex[65]) {
    struct digest d={{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19},0,0,{0}};
    unsigned char buf[32768];ssize_t n;
    while((n=read(fd,buf,sizeof(buf)))!=0){if(n<0){if(errno==EINTR)continue;return -1;}update(&d,buf,(size_t)n);}
    uint64_t bits=d.bytes*8;
    unsigned char end[128]={0x80};size_t z=d.used<56?56-d.used:120-d.used;
    for(size_t i=0;i<8;i++)end[z+i]=(unsigned char)(bits>>(56-i*8));
    update(&d,end,z+8);
    for(size_t i=0;i<8;i++)snprintf(hex+i*8,9,"%08x",d.s[i]);
    return 0;
}
