%global nspr_version 4.21.0
# adjust to the very latest build needed
%global nspr_build_version -1
%global nss_util_version 3.44

Summary:          Network Security Services Utilities Library
Name:             nss-util
Version:          %{nss_util_version}.0
Release:          1%{?dist}
License:          MPLv2.0
URL:              http://www.mozilla.org/projects/security/pki/nss/
Group:            System Environment/Libraries
Requires:         nspr >= %{nspr_version}%{nspr_build_version}
BuildRoot:        %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:    nspr-devel >= %{nspr_version}%{nspr_build_version}
BuildRequires:    zlib-devel
BuildRequires:    pkgconfig
BuildRequires:    gawk
BuildRequires:    psmisc
BuildRequires:    perl

Source0:          %{name}-%{nss_util_version}.tar.gz
# The nss-util tar ball is a subset of nss-{version}.tar.gz
# We use the nss-split-util.sh script for keeping only what we need.
# nss-util is produced via nss-split-util.sh {name}-{version}
# Detailed Steps:
# rhpkg clone nss-util
# cd nss-util
# Make the source tarball for nss-util out of the nss one:
# sh ./nss-split-util.sh ${version}
# A file named ${name}-${version}.tar.gz should appear
# ready to upload to the lookaside cache.
Source1:          nss-split-util.sh
Source2:          nss-util.pc.in
Source3:          nss-util-config.in

Patch2:           add-relro-linker-option.patch
Patch3:           nss-util-noexecstack.patch
Patch5:           hasht-dont-include-prtypes.patch
Patch7: pkcs1sig-include-prtypes.patch
# To revert change in:
# https://bugzilla.mozilla.org/show_bug.cgi?id=1377940
Patch9: nss-util-sql-default.patch
# https://bugzilla.mozilla.org/show_bug.cgi?id=1546229
# https://bugzilla.mozilla.org/show_bug.cgi?id=1473806
Patch10: nss-util-ike-patch.patch
Patch11: nss-util-fix-public-key-from-priv.patch

%description
Utilities for Network Security Services and the Softoken module

# We shouln't need to have a devel subpackage as util will be used in the
# context of nss or nss-softoken. keeping to please rpmlint.
# 
%package devel
Summary:          Development libraries for Network Security Services Utilities
Group:            Development/Libraries
Requires:         nss-util = %{version}-%{release}
Requires:         nspr-devel >= %{nspr_version}
Requires:         pkgconfig

%description devel
Header and library files for doing development with Network Security Services.


%prep
%setup -q -n %{name}-%{nss_util_version}
%patch2 -p0 -b .relro
# The compiler on ppc/ppc64 builders for RHEL-6 doesn't accept -z as a
# linker option.  Use -Wl,-z instead.
%patch3 -p0 -b .noexecstack
%patch5 -p0 -b .prtypes
%patch7 -p0 -b .include_prtypes
pushd nss
%patch9 -p1 -R -b .sql-default
%patch10 -p1 -b .ike_mechs
popd
%patch11 -p1 -b .pub_priv_mechs



%build

# Enable compiler optimizations and disable debugging code
BUILD_OPT=1
export BUILD_OPT

# Uncomment to disable optimizations
#RPM_OPT_FLAGS=`echo $RPM_OPT_FLAGS | sed -e 's/-O2/-O0/g'`
#export RPM_OPT_FLAGS

# Generate symbolic info for debuggers
XCFLAGS=$RPM_OPT_FLAGS
export XCFLAGS

PKG_CONFIG_ALLOW_SYSTEM_LIBS=1
PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1

export PKG_CONFIG_ALLOW_SYSTEM_LIBS
export PKG_CONFIG_ALLOW_SYSTEM_CFLAGS

NSPR_INCLUDE_DIR=`/usr/bin/pkg-config --cflags-only-I nspr | sed 's/-I//'`
NSPR_LIB_DIR=`/usr/bin/pkg-config --libs-only-L nspr | sed 's/-L//'`

export NSPR_INCLUDE_DIR
export NSPR_LIB_DIR

NSS_USE_SYSTEM_SQLITE=1
export NSS_USE_SYSTEM_SQLITE

NSS_BUILD_UTIL_ONLY=1
export NSS_BUILD_UTIL_ONLY

# gtests intended for nss (higher layers) as they test ssl/tls
export NSS_DISABLE_GTESTS=1

%ifarch x86_64 ppc64 ia64 s390x sparc64
USE_64=1
export USE_64
%endif

# make util
%{__make} -C ./nss/coreconf
%{__make} -C ./nss

# Set up our package file
%{__mkdir_p} ./dist/pkgconfig
%{__cat} %{SOURCE2} | sed -e "s,%%libdir%%,%{_libdir},g" \
                          -e "s,%%prefix%%,%{_prefix},g" \
                          -e "s,%%exec_prefix%%,%{_prefix},g" \
                          -e "s,%%includedir%%,%{_includedir}/nss3,g" \
                          -e "s,%%NSPR_VERSION%%,%{nspr_version},g" \
                          -e "s,%%NSSUTIL_VERSION%%,%{version},g" > \
                          ./dist/pkgconfig/nss-util.pc

NSSUTIL_VMAJOR=`cat nss/lib/util/nssutil.h | grep "#define.*NSSUTIL_VMAJOR" | awk '{print $3}'`
NSSUTIL_VMINOR=`cat nss/lib/util/nssutil.h | grep "#define.*NSSUTIL_VMINOR" | awk '{print $3}'`
NSSUTIL_VPATCH=`cat nss/lib/util/nssutil.h | grep "#define.*NSSUTIL_VPATCH" | awk '{print $3}'`

export NSSUTIL_VMAJOR
export NSSUTIL_VMINOR
export NSSUTIL_VPATCH

%{__cat} %{SOURCE3} | sed -e "s,@libdir@,%{_libdir},g" \
                          -e "s,@prefix@,%{_prefix},g" \
                          -e "s,@exec_prefix@,%{_prefix},g" \
                          -e "s,@includedir@,%{_includedir}/nss3,g" \
                          -e "s,@MOD_MAJOR_VERSION@,$NSSUTIL_VMAJOR,g" \
                          -e "s,@MOD_MINOR_VERSION@,$NSSUTIL_VMINOR,g" \
                          -e "s,@MOD_PATCH_VERSION@,$NSSUTIL_VPATCH,g" \
                          > ./dist/pkgconfig/nss-util-config

chmod 755 ./dist/pkgconfig/nss-util-config


%install

%{__rm} -rf $RPM_BUILD_ROOT

# There is no make install target so we'll do it ourselves.

%{__mkdir_p} $RPM_BUILD_ROOT/%{_includedir}/nss3
%{__mkdir_p} $RPM_BUILD_ROOT/%{_includedir}/nss3/templates
%{__mkdir_p} $RPM_BUILD_ROOT/%{_libdir}
%{__mkdir_p} $RPM_BUILD_ROOT/%{_libdir}/nss3
%{__mkdir_p} $RPM_BUILD_ROOT/%{_libdir}/pkgconfig
%{__mkdir_p} $RPM_BUILD_ROOT/%{_bindir}

for file in libnssutil3.so
do
  %{__install} -p -m 755 dist/*.OBJ/lib/$file $RPM_BUILD_ROOT/%{_libdir}
done

# Copy the include files we want
# The util headers, the rest come from softokn and nss
for file in dist/public/nss/*.h
do
  %{__install} -p -m 644 $file $RPM_BUILD_ROOT/%{_includedir}/nss3
done

# Copy the template files we want
for file in dist/private/nss/templates.c
do
  %{__install} -p -m 644 $file $RPM_BUILD_ROOT/%{_includedir}/nss3/templates
done

# Copy the package configuration files
%{__install} -p -m 644 ./dist/pkgconfig/nss-util.pc $RPM_BUILD_ROOT/%{_libdir}/pkgconfig/nss-util.pc
%{__install} -p -m 755 ./dist/pkgconfig/nss-util-config $RPM_BUILD_ROOT/%{_bindir}/nss-util-config

%clean
%{__rm} -rf $RPM_BUILD_ROOT

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%files
%defattr(-,root,root)
%{_libdir}/libnssutil3.so

%files devel
%defattr(-,root,root)
# package configuration files
%{_libdir}/pkgconfig/nss-util.pc
%{_bindir}/nss-util-config

# co-owned with nss
%dir %{_includedir}/nss3
# these are marked as public export in nss/lib/util/manifest.mk
%{_includedir}/nss3/base64.h
%{_includedir}/nss3/ciferfam.h
%{_includedir}/nss3/eccutil.h
%{_includedir}/nss3/hasht.h
%{_includedir}/nss3/nssb64.h
%{_includedir}/nss3/nssb64t.h
%{_includedir}/nss3/nsslocks.h
%{_includedir}/nss3/nssilock.h
%{_includedir}/nss3/nssilckt.h
%{_includedir}/nss3/nssrwlk.h
%{_includedir}/nss3/nssrwlkt.h
%{_includedir}/nss3/nssutil.h
%{_includedir}/nss3/pkcs11.h
%{_includedir}/nss3/pkcs11f.h
%{_includedir}/nss3/pkcs11n.h
%{_includedir}/nss3/pkcs11p.h
%{_includedir}/nss3/pkcs11t.h
%{_includedir}/nss3/pkcs11u.h
%{_includedir}/nss3/pkcs11uri.h
%{_includedir}/nss3/pkcs1sig.h
%{_includedir}/nss3/portreg.h
%{_includedir}/nss3/secasn1.h
%{_includedir}/nss3/secasn1t.h
%{_includedir}/nss3/seccomon.h
%{_includedir}/nss3/secder.h
%{_includedir}/nss3/secdert.h
%{_includedir}/nss3/secdig.h
%{_includedir}/nss3/secdigt.h
%{_includedir}/nss3/secerr.h
%{_includedir}/nss3/secitem.h
%{_includedir}/nss3/secoid.h
%{_includedir}/nss3/secoidt.h
%{_includedir}/nss3/secport.h
%{_includedir}/nss3/utilmodt.h
%{_includedir}/nss3/utilpars.h
%{_includedir}/nss3/utilparst.h
%{_includedir}/nss3/utilrename.h
%{_includedir}/nss3/templates/templates.c

%changelog
* Mon Aug 19 2019 Bob Relyea <rrelyea@redhat.com> - 3.44.0-1
- Rebase to NSS 3.44.0 for Firefox 68

* Wed Mar  7 2018 Daiki Ueno <dueno@redhat.com> - 3.36.0-1
- Rebase to NSS 3.36.0

* Wed Feb 28 2018 Daiki Ueno <dueno@redhat.com> - 3.36.0-0.1.beta
- Rebase to NSS 3.36 BETA

* Mon Dec  4 2017 Daiki Ueno <dueno@redhat.com> - 3.34.0-1
- Rebase to NSS 3.34.0

* Fri Apr  7 2017 Daiki Ueno <dueno@redhat.com> - 3.28.4-1
- Rebase to NSS 3.28.4 to accommodate base64 encoding fix

* Fri Feb 24 2017 Daiki Ueno <dueno@redhat.com> - 3.28.3-1
- Rebase to NSS 3.28.3
- Package new header eccutil.h

* Wed Nov 23 2016 Daiki Ueno <dueno@redhat.com> - 3.27.1-3
- Tolerate policy file without last empty line

* Tue Oct  4 2016 Daiki Ueno <dueno@redhat.com> - 3.27.1-2
- Add missing source files

* Tue Oct  4 2016 Daiki Ueno <dueno@redhat.com> - 3.27.1-1
- Rebase to NSS 3.26.0
- Remove upstreamed patch for CVE-2016-1950
- Remove p-disable-md5-590364-reversed.patch for bug 1335915

* Mon Feb 22 2016 Kai Engert <kaie@redhat.com> - 3.21.0-2
- Added upstream patch for CVE-2016-1950

* Mon Jan 18 2016 Elio Maldonado <emaldona@redhat.com> - 3.21.0-1
- Rebase to nss-util from nss 3.21
- Resolves: Bug 1297890 - Rebase RHEL 6.8 to NSS-util 3.21 in preparation for Firefox 45

* Fri Oct 16 2015 Elio Maldonado <emaldona@redhat.com> - 3.19.1-2
- Resolves: Bug 1269356 - CVE-2015-7182 CVE-2015-7181

* Sat Jun 06 2015 Elio Maldonado <emaldona@redhat.com> - 3.19.1-1
- Rebase to nss-3.19.1
- Resolves: Bug 1224450

* Mon Mar 23 2015 Elio Maldonado <emaldona@redhat.com> - 3.18.0-1
- Resolves: Bug 1200937 - [RHEL6.6] nss-util 3.18 rebase required for firefox 38 ESR

* Fri Nov 21 2014 Elio Maldonado <emaldona@redhat.com> - 3.16.2.3-2
- Fix the required nspr version to be 4.10.6
- Resolves: Bug 1158160 - Upgrade to NSS 3.16.2.3 for Firefox 31.3

* Thu Nov 13 2014 Elio Maldonado <emaldona@redhat.com> - 3.16.2.3-1
- Resolves: Bug 1158160 - Upgrade to NSS 3.16.2.3 for Firefox 31.3
- Remove patches rendered obsolete by the rebase

* Fri Sep 26 2014 Kai Engert <kaie@redhat.com> - 3.16.1-3
- Fix version number in previous changelog item.
- Rebuild to increase release version number.

* Tue Sep 23 2014 Elio Maldonado <emaldona@redhat.com> - 3.16.1-2
- Resolves: bug 1145432 - CVE-2014-1568

* Thu May 22 2014 Elio Maldonado <emaldona@redhat.com> - 3.15.3-6
- Update to nss-3.16.1
- Resolves: rhbz#1099619 - Rebase nss in RHEL 6.6 to NSS 3.16.1

* Mon Apr 21 2014 Elio Maldonado <emaldona@redhat.com> - 3.15.3-4
- nssutil_growList and nssutil_ReadSecmodDB cleanup
- Resolves: Bug 1019529 - New defect found in nss-util-3.14.0.0-2.el6

* Wed Mar 26 2014 Elio Maldonado <emaldona@redhat.com> - 3.15.3-3
- Apply the patch for the pluggable ecc fix
- Resolves: Bug 1057224 - Pluggable ECC in NSS not enabled on RHEL 6 and above

* Tue Mar 25 2014 Elio Maldonado <emaldona@redhat.com> - 3.15.3-2
- Add nss-util portion of a fix for pluggable ecc bug in nss and nss-util
- Resolves: Bug 1057224 - Pluggable ECC in NSS not enabled on RHEL 6 and above

* Mon Nov 25 2013 Elio Maldonado <emaldona@redhat.com> - 3.15.3-1
- Update to NSS_3_15_3_RTM
- Resolves: rhbz#1032472 - CVE-2013-5605 CVE-2013-5606 CVE-2013-1741

* Mon Oct 14 2013 Elio Maldonado <emaldona@redhat.com> - 3.15.1-3
- Preserve existing permissions when replacing existing pkcs11.txt file, but keep strict default permissions for new files
- Resolves: rhbz#990631 - file permissions of pkcs11.txt/secmod.db must be kept when modified by NSS

* Sat Sep 07 2013 Elio Maldonado <emaldona@redhat.com> - 3.15.1-2
- Require nspr-4.10.0
- Related: rhbz#1002644 - Rebase RHEL 6 to NSS-UTIL 3.15.1 (for FF 24.x)

* Thu Aug 29 2013 Elio Maldonado <emaldona@redhat.com> - 3.14.3-5
- Update to NSS_3_15_1_RTM
- Resolves: rhbz#1002644 - Rebase RHEL 6 to NSS-UTIL 3.15.1 (for FF 24.x)

* Tue Jul 23 2013 Elio Maldonado <emaldona@redhat.com> - 3.14.3-4
- Resolves: rhbz#976572 - Pick up various upstream GCM code fixes applied since nss-3.14.3 was released

* Mon Jul 15 2013 Elio Maldonado <emaldona@redhat.com> - 3.14.3-3
- Resolves: rhbz#975755 - nssutil_ReadSecmodDB leaks memory

* Fri May 31 2013 Elio Maldonado <emaldona@redhat.com> - 3.14.3-2
- Revert to accepting MD5 on digital signatures by default
- Resolves: rhbz#918136 - nss 3.14 - MD5 hash algorithm disabled

* Fri Mar 22 2013 Elio Maldonado <emaldona@redhat.com> - 3.14.3-1
- Update to NSS_3_14_3_RTM
- Resolves: rhbz#919174 - Rebase to 3.14.3 as part of the fix for the lucky-13 issue

* Wed Jan 09 2013 Elio Maldonado <emaldona@redhat.com> - 3.14.0.0-2
- Fix inconstent n-v-r tag number numbers

* Thu Oct 11 2012 Elio Maldonado <emaldona@redhat.com> - 3.13.5-3
- Update to nss-3.14.0.0-1
- Add temporary patch so utilmod doesn't include any headers from softoken
- Keep the hasht.h from current nss-softokn-devel
- Remove the long obsoleted nss-nolocalsql.patch

* Thu Jun 21 2012 Elio Maldonado <emaldona@redhat.com> - 3.13.5-2
- Resolves: rhbz#833480 - revert unwanted change to nss-util.pc.in

* Wed Jun 20 2012 Elio Maldonado <emaldona@redhat.com> - 3.13.5-1
- Update to NSS_3_13_5_RTM
- Resolves: rhbz#833480 - Update nss-util on RHEL 6.x to NSS 3.13.5 for Mozilla 10.0.6
- Add -L${libdir}/nss3 to Libs: line in nspr.pc.in

* Wed Mar 07 2012 Elio Maldonado <emaldona@redhat.com> - 3.13.3-2
- Resolves: rhbz#799192 - Update to 3.13.3
- Update minimum nspr version for Requires and BuildRequires to 4.9
- Fix version/release in changelog to match the Version and Release tags, now 3.13.3-2

* Mon Mar 05 2012 Elio Maldonado <emaldona@redhat.com> - 3.13.1-5
- Resolves: rhbz#799192 - Update to 3.13.3

* Mon Jan 30 2012 Martin Stransky <stransky@redhat.com> 3.13.1-2
- Rebuild for NSPR 4.8.9

* Wed Jan 18 2012 Elio Maldonado <emaldona@redhat.com> - 3.13.1-1
- Resolves: Bug 773056 - Update to 3.13.1

* Tue Sep 27 2011 Elio Maldonado <emaldona@redhat.com> - 3.12.10-2
- Add relro support for executables and shared libraries

* Wed Jul 06 2011 Elio Maldonado <emaldona@redhat.com> - 3.12.10-1
- Update to 3.12.10

* Mon Jan 17 2011 Elio Maldonado <emaldona@redhat.com> - 3.12.9-1
- Update to 3.12.9

* Thu Sep 30 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.8-1
- Update to 3.12.8

* Thu Aug 26 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.7-1
- Update to 3.12.7

* Thu Mar 04 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.6-1
- Update to 3.12.6

* Wed Feb 24 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.5.99-1.1
- Require nspr >= 4.8.2 until 4.8.4 gets added to the buildroot

* Wed Feb 24 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.5.99-1
- Update to NSS_3_12_6_RC1

* Mon Jan 18 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.5-1.4
- Added a missing patch file

* Mon Jan 18 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.5-1.3
- Related: rhbz 551784 - Fix incorrectly formatted tag

* Mon Jan 18 2010 Elio Maldonado <emaldona@redhat.com> - 3.12.5-1.2
- Related: rhbz 551784 - Fix in nss-util-config.in 

* Thu Dec 03 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.5-1.1
- Update to 3.12.5

* Thu Sep 10 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.4-8
- Retagging for a chained build with nss-softokn and nss

* Thu Sep 10 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.4-5
- Restoring -rpath-link to nss-util-config

* Tue Sep 08 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.4-4
- Installing shared libraries to %%{_libdir}

* Sat Sep 05 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.4-3
- Remove symbolic links to shared libraries from devel - 521155
- Apply nss-nolocalsql patch subset for nss-util
- No rpath-link in nss-util-config

* Fri Sep 04 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.4-2
- Retagging for a chained build

* Thu Sep 03 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.4-1
- Update to 3.12.4
- Don't require sqlite

* Thu Aug 27 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.3.99.3-15
- Bump the release number for a chained build of nss-util, nss-softokn and nss

* Thu Aug 27 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.3.99.3-14
- Cleanup nss-util-config.in

* Thu Aug 27 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.3.99.3-13
- nss-util-devel doesn't require nss-devel

* Wed Aug 26 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.3.99.3-12
- bump to unique nvr

* Wed Aug 26 2009 Elio Maldonado<emaldona@redhat.com> - 3.12.3.99.3-11
- Remove spurious executable permissions from nss-util-config
- Shorten some descriptions to keep rpmlint happy

* Mon Aug 24 2009 Dennis Gilmore <dennis@ausil.us> 3.12.3.99.3-10
- dont include the headers in nss-util only in the -devel package
- nss-util-devel Requires nss-devel since its only providing a subset of the headers.

* Thu Aug 20 2009 Dennis Gilmore <dennis@ausil.us> 3.12.3.99.3-9
- Provide nss-devel since we obsolete it

* Wed Aug 19 2009 Elio Maldonado <emaldona@redhat.com> 3.12.3.99.3-8.1
- nss-util-devel obsoletes nss-devel < 3.12.3.99.3-8

* Wed Aug 19 2009 Elio Maldonado <emaldona@redhat.com> 3.12.3.99.3-8
- Initial build
