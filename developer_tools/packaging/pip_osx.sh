MACOSX_DEPLOYMENT_TARGET=10.9;
export MACOSX_DEPLOYMENT_TARGET;

BUILD_DIR="$HOME/build_raven_libs"
INSTALL_DIR="$HOME/raven_libs"
mkdir -p $BUILD_DIR
cd $BUILD_DIR
curl -O -- https://bootstrap.pypa.io/get-pip.py
python get-pip.py --user
PATH="$PATH:$HOME/Library/Python/2.7/bin"
pip install virtualenv --user
virtualenv $INSTALL_DIR
source $INSTALL_DIR/bin/activate
pip install numpy==1.11.0 h5py==2.6.0 scipy==0.17.1 scikit-learn==0.17.1 matplotlib==1.5.1


curl -O -L -- http://downloads.sourceforge.net/project/pcre/pcre/8.35/pcre-8.35.tar.bz2
tar -xjf pcre-8.35.tar.bz2
cd pcre-8.35/
./configure --prefix=$INSTALL_DIR
make
make install


cd $BUILD_DIR
curl -O -L -- https://downloads.sourceforge.net/project/swig/swig/swig-3.0.12/swig-3.0.12.tar.gz
tar -xvzf swig-3.0.12.tar.gz
cd swig-3.0.12/
./configure --prefix="$INSTALL_DIR"
make
make install

export MPLBACKEND="TkAgg"
